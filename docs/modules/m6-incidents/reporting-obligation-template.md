# ReportingObligationTemplate

`incidents.models.reporting_obligation_template.ReportingObligationTemplate`

The rule that turns incident facts into an owed deliverable : **regime + authority + stage + clock + trigger conditions + content checklist**. One row per obligation an organisation can owe, expressed as **data rather than as code**, because NIS2 transposition, the DORA regulatory technical standards and every sector regime differ per jurisdiction and per entity type. A French energy operator and a German bank owe different filings on different clocks to different bodies, and neither of them should need a release of Cairn to say so.

A template generates nothing by itself. It is matched against an [Incident](incident.md) at triage (and re-matched on the two events listed under [When generation runs](#when-generation-runs)), and each match produces one [IncidentNotification](incident-notification.md) obligation whose legal terms are **snapshotted at creation**. Editing a template two years later changes what future incidents generate and changes **nothing** about a filing already made.

File: `incidents/models/reporting_obligation_template.py`

Phase **2**. `BaseModel` subclass : UUID PK, sequential `reference` (prefix **`ROBT`**, e.g. `ROBT-1`), `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the core **`default` 4-state lifecycle**. `workflow_perm_namespace` is overridden to `incidents.response_plan`, because the default `app_label.model_name` would spell `incidents.reportingobligationtemplate`, which matches no feature in `PERMISSION_REGISTRY`. Phase 2 introduces **no new permission feature** (RG-INC-39).

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `ROBT-N`, unique | Business reference |
| `name` | string | required, max 255 | Human label, e.g. `NIS2 early warning (24h) - ANSSI`. What the operator sees in the obligation list before reading anything else. |
| `regime` | enum | required | `NotificationRegime` (declared in `incidents/constants.py`, documented on [IncidentNotification](incident-notification.md)). The legal basis the obligation arises from. **Copied onto every generated obligation.** |
| `recipient_kind` | enum | required | `NotificationRecipientKind` : who receives the filing. Copied onto every generated obligation. |
| `legal_reference` | string | optional, max 255, blank default | Article citation, e.g. `NIS2 Art. 23(4)(a)`, `GDPR Art. 33(1)`. Copied onto every generated obligation, and the string an auditor greps the register for. |
| `clock_anchor` | enum | required, default `awareness_at` | `ClockAnchor` : which timestamp starts the statutory clock. Copied onto every generated obligation. |
| `clock_hours` | int | optional, positive | Statutory delay in hours from the anchor : `24`, `72`, `720` (one month). Null **if and only if** `no_fixed_deadline` is `True`, validated in `clean()` and mirrored by a DB `CheckConstraint`. |
| `no_fixed_deadline` | boolean | required, default `False` | The obligation is a "without undue delay" duty with no computable deadline (GDPR Art. 33(2), Art. 34(1), NIS2 Art. 23(1) to recipients). Generated obligations then carry `due_at = NULL`, are **never** counted late, and appear in their own *no statutory deadline* bucket rather than vanishing from every are-we-late query. Never fabricate a deadline for an obligation that legally has none. |
| `depends_on_regime` | enum | optional, blank default | The sibling regime whose **first filing** anchors this one. Mandatory (`clean()`) when `clock_anchor = previous_stage`. NIS2 Art. 23(4)(d) : the final report is due one month after the incident **notification**, not one month after awareness. |
| `jurisdiction_country` | string | optional, max 100, blank default | Restricts the template to incidents in a jurisdiction. Blank means *any*. Matched against the incident's jurisdiction, resolved from its scopes and affected sites. |
| `min_severity` | enum | optional, blank default | `context.constants.Criticality` floor. Blank means *any severity*. Compared on the ordered scale `low < medium < high < critical`, never as a string. |
| `requires_significant` | boolean | required, default `False` | Only fires when `Incident.is_significant` is `True` (NIS2 Art. 23(3)). A `null` verdict is **not** a match : an undetermined significance never silently generates or suppresses a NIS2 duty. |
| `requires_personal_data` | boolean | required, default `False` | Only fires when `Incident.personal_data_involved` is `True` (GDPR) |
| `requires_high_risk` | boolean | required, default `False` | Only fires when [PersonalDataBreach](personal-data-breach.md) `.high_risk_to_rights` is `True` (GDPR Art. 34(1)). A `null` verdict is not a match. |
| `requires_cross_border` | boolean | required, default `False` | Only fires when `Incident.cross_border_impact` is `True`. **See [The two Incident fields this entity needs](#the-two-incident-fields-this-entity-needs)** : that field is added to `Incident` by this phase, and without it the flag has nothing to evaluate against. |
| `controller_roles` | JSON | optional, `default=list` | List of `ControllerRole` values restricting a GDPR template to `controller`, `joint_controller` or `processor`. Empty means *any*. This is what separates a controller's Art. 33(1) duty from a processor's Art. 33(2) duty : see [PersonalDataBreach](personal-data-breach.md#controller_role-decides-which-obligations-exist-at-all). |
| `applicable_categories` | JSON | optional, `default=list` | List of `risks.constants.ThreatCategory` values restricting the template to certain incident categories. Empty means *all 23*. |
| `content_requirements` | text | optional, HTML | The legal checklist of what the filing must contain. **Copied onto every generated obligation**, and rendered next to the drafting field so the drafter never leaves the page to find out what Art. 33(3) requires. |
| `order` | int | required, default 0 | Display and generation order within a regime, so the 24h early warning is listed above the 72h notification rather than alphabetically |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (core `default`) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

`JSONField` is used for the three list fields rather than `ArrayField` so that `core.settings_test` (SQLite in memory) runs the module unchanged. Each list is validated element-by-element in `clean()` against the corresponding enum, so a typo is rejected at save time rather than silently matching nothing forever.

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `authority` | FK, `PROTECT`, optional | [ReportingAuthority](reporting-authority.md) | `obligation_templates` | The body the filing goes to. Null for templates whose recipient is not an authority (`data_subject`, `customer`, `public`). `PROTECT` : an authority with templates cannot be deleted. |

| Reverse accessor | Source | Description |
|---|---|---|
| `obligations` | [IncidentNotification](incident-notification.md) `.template` (FK, `PROTECT`, optional) | Every obligation ever generated from this template. `PROTECT` is load-bearing : a template with instantiated obligations can never be deleted, so the provenance of a two-year-old filing stays resolvable. |

### Meta

- `ordering = ["regime", "order", "name"]`
- `UniqueConstraint(["regime", "recipient_kind", "authority", "jurisdiction_country"], name="unique_obligation_template")`

The unique constraint is a duplicate guard, not a modelling statement, and it has a known weakness worth stating rather than discovering : `authority` is nullable, and PostgreSQL treats `NULL`s as distinct in a unique index by default, so two templates with `authority = NULL` and otherwise identical keys are **not** rejected. Declare the constraint with `nulls_distinct=False` (PostgreSQL 15+), or split it into two conditional constraints (one with `condition=Q(authority__isnull=True)`), and do not rely on it as the only defence : the generator is independently idempotent, as described under [Idempotence](#idempotence).

## Enumerations

### ClockAnchor

Declared in `incidents/constants.py` and shared with [IncidentNotification](incident-notification.md).

| Value | Label |
|---|---|
| `occurred_at` | Occurrence |
| `detected_at` | Detection |
| `awareness_at` | Awareness |
| `significance_determined_at` | Significance determination |
| `previous_stage` | Previous filing |

`awareness_at` is the default and the correct anchor for GDPR Art. 33(1) and NIS2 Art. 23(4)(a)-(b). `detected_at` exists because a handful of contractual clauses genuinely are written against technical detection, **not** because it is ever an acceptable anchor for a statutory clock : see [Incident](incident.md#the-two-clocks). `previous_stage` exists solely for NIS2 Art. 23(4)(d), and it is the reason `depends_on_regime` and `IncidentNotification.depends_on` exist : without it, every NIS2 final-report deadline in the register would be a month too early.

`NotificationRegime`, `NotificationRecipientKind` and `ControllerRole` are declared once (in `incidents/constants.py` for the first two, and documented on [PersonalDataBreach](personal-data-breach.md) for the third) and are not repeated here.

## Trigger conditions

A template matches an incident when **every** declared condition holds. The evaluation is a flat conjunction, in this order, short-circuiting on the first failure:

1. The template is in a `reportable()` lifecycle state (RG-INC-30). A draft template is a work in progress, not a legal position.
2. Its `authority`, when set, is in a `reportable()` state (see [ReportingAuthority](reporting-authority.md#obligation-generation)).
3. `jurisdiction_country` is blank, or equals the incident's resolved jurisdiction.
4. `min_severity` is blank, or `Criticality` ranks the incident's `severity` at or above it.
5. `applicable_categories` is empty, or contains the incident's `category`.
6. `requires_significant` is `False`, or `Incident.is_significant` is exactly `True`.
7. `requires_personal_data` is `False`, or `Incident.personal_data_involved` is `True`.
8. `requires_high_risk` is `False`, or the incident's [PersonalDataBreach](personal-data-breach.md) exists and its `high_risk_to_rights` is exactly `True`.
9. `requires_cross_border` is `False`, or `Incident.cross_border_impact` is exactly `True`.
10. `controller_roles` is empty, or the incident's `PersonalDataBreach` exists and its `controller_role` is in the list.

Three-state booleans are compared to `True` explicitly, never with a truthiness test. `None` means *not yet determined*, and an undetermined verdict must neither generate an obligation nor suppress one : the operator is asked for the verdict, and generation is re-run when it arrives.

Conditions 8 and 10 evaluate to *no match* when no `PersonalDataBreach` record exists, which is the correct behaviour : a GDPR-conditioned template cannot fire on an incident that has not been qualified under GDPR at all.

### The honest limitation, stated rather than hidden

**Real regulatory rules are disjunctive and conditional. This model is a flat conjunction. The gap is deliberate, and it is paid for with near-duplicate templates rather than with a rule expression language.**

Two shapes the field cannot express directly:

- **Disjunction.** *"Significant **or** affecting more than N users."* There is no `OR` between conditions. The organisation writes **two** templates for the same regime, one with `requires_significant=True` and one with a `min_severity` that stands in for the user-count threshold, and accepts that an incident matching both generates one obligation, not two, because the generator de-duplicates on `(incident, regime, recipient)` (see [Idempotence](#idempotence)).
- **Negative conditions.** *"Unless the data was encrypted with state-of-the-art cryptography"* (GDPR Art. 34(3)(a)). There is no `unless`. The module takes the deliberately stricter route : the Art. 34 obligation is **still generated**, and the exemption is discharged through the obligation's own `not_required` decision with the exemption ground and its written justification as the mandatory rationale (see [PersonalDataBreach](personal-data-breach.md#article-343-exemptions)). An exemption that is recorded and approved is audit evidence; an exemption that silently suppresses an obligation is an absence nobody can review.

A rule expression language would express both. It would also need a parser, an evaluator, a test surface, an editing UI, a migration path for stored expressions and a way to explain to an operator at 02:00 why a rule did or did not fire. The design refuses to build one, and reconsiders **only** if a real customer's regime cannot be expressed at all - not because expressing it takes three templates instead of one. The cost is honest and bounded : a catalogue with some redundancy, and a `name` field that has to earn its keep by saying which variant a row is.

### The two Incident fields this entity needs

`requires_cross_border` had nothing to evaluate against in the original design, and NIS2 Art. 23(4)(a) requires the 24-hour early warning to state whether the incident is **suspected of being caused by an unlawful or malicious act** - a verdict no entity recorded. Phase 2 therefore adds two fields to [Incident](incident.md), alongside `is_significant`:

| Field | Type | Description |
|---|---|---|
| `cross_border_impact` | `BooleanField(null=True, default=None)` | Three-state. The incident affects, or is likely to affect, entities or data subjects in more than one Member State. This is what `requires_cross_border` evaluates against. |
| `cross_border_justification` | `TextField(blank=True, default="")` | Written reasoning for the verdict, mandatory once `cross_border_impact` is non-null |
| `suspected_malicious` | `BooleanField(null=True, default=None)` | Three-state. The incident is suspected to be caused by an unlawful or malicious act (NIS2 Art. 23(4)(a)). |
| `suspected_malicious_justification` | `TextField(blank=True, default="")` | Written reasoning for the verdict, mandatory once `suspected_malicious` is non-null |

Both are **three-state on purpose**. "We do not yet know whether this was malicious" is the true state of the world at hour 6 of a ransomware incident, and a two-state boolean would force the operator to assert `False` and would make an unanswered question indistinguishable from a considered negative.

`cross_border_impact` is deliberately **not** the same field as `PersonalDataBreach.cross_border_eu`. The latter is cross-border **processing** within the meaning of GDPR Art. 4(23), a term of art about where a controller is established and which data subjects are affected. The former is operational cross-border **impact**, and it exists for NIS2 incidents that involve no personal data at all, where no `PersonalDataBreach` record exists to carry anything.

Both fields gate the **`drafted -> sent`** transition of any obligation whose `regime = nis2_early_warning` (gate **G-03** on [IncidentNotification](incident-notification.md)) : the filing may not be recorded as sent while `is_significant`, `suspected_malicious` or `cross_border_impact` is `None`, because the form the operator is filing has a mandatory field for each. The gate lives in the `transition_to()` override on [IncidentNotification](incident-notification.md), per RG-INC-08, never in `Transition.form_class`. It is a **precondition of sending**, not of generating : the obligation is created at triage precisely so that the 24-hour clock starts running while the verdicts are still being formed.

> `Incident.cross_border_impact`, `cross_border_justification`, `suspected_malicious` and `suspected_malicious_justification` must be declared in [incident.md](incident.md)'s field table and in `incidents/models/incident.py` for this entity's `requires_cross_border` flag and the early-warning send gate to have any meaning.

## When generation runs

Generation is idempotent and runs at exactly three points:

1. **The `detected -> triaged` transition on the incident** (RG-INC-11, RG-INC-19), inside the transition's atomic block. This is the main path : the obligation set is known as soon as severity, category and the incident manager are.
2. **On `INCIDENT_SEVERITY_RAISED`**, when `severity` moves above `initial_severity` after triage. A `min_severity` template that did not match at triage matches now, and its absence would be a missed 24-hour NIS2 clock rather than a cosmetic gap.
3. **On the `under_qualification -> confirmed` transition of a [PersonalDataBreach](personal-data-breach.md)**, when `controller_role` and `high_risk_to_rights` become known and conditions 8 and 10 can finally be evaluated.

Each run creates obligations in `draft` and then transitions each new row to **`assessed`** ("To decide") with `enforce_permission=False`, in the same atomic block. **No row is ever created directly in `assessed`** : `BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`) and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the `StepKind.DRAFT` step, so an insert that names another step in `workflow_state` either gets snapped back or, if it happens to stick, leaves no `core.LifecycleEvent` and no evidence the obligation was ever opened.

```python
with transaction.atomic():
    for template in matching_templates:
        obligation, created = _get_or_create_obligation(incident, template)
        if created:
            obligation.transition_to("assessed", user, enforce_permission=False)
```

An obligation left in `draft` would be `deletable=True`, would not appear in the *To decide* bucket the whole "an unanswered obligation is visible rather than absent" argument rests on, and would still carry `decision = undecided`, silently blocking the RG-INC-14 closure gate with no visible reason. A test asserts that the generator yields rows in `assessed`, and a second test asserts that a bare `IncidentNotification.objects.create(...)` does **not**.

### Idempotence

The generator performs an explicit `get_or_create`-style lookup on `(incident, regime, recipient_key)` **in Python**, and [IncidentNotification](incident-notification.md#uniqueness-of-an-obligation) backs it with `UniqueConstraint(fields=["incident", "regime", "recipient_key"])`.

`recipient_key` is a derived, never-null discriminator precisely so the constraint bites. Keying the constraint on the recipient foreign keys themselves would not work : both are `NULL` on every auto-generated authority obligation, PostgreSQL treats `NULL`s as distinct in a unique index by default, and re-running triage would insert a second identical row rather than being rejected. The nullable-FK caveat still applies to this entity's own `unique_obligation_template` constraint, which is why that one is written the way it is.

Re-running generation therefore:

- **never** duplicates an existing obligation for the same `(incident, regime, recipient)`;
- **never** rewrites an existing obligation's snapshotted terms, even if the template has changed in the meantime;
- **never** touches an obligation that has left `assessed` : a decision already taken is not revisited by a generator.

## Snapshot on generation

> **RG-INC-30.** The obligation terms generated from a template - `regime`, `recipient_kind`, `obligation_reference` (from `legal_reference`), `clock_anchor`, `deadline_hours` (from `clock_hours`), `no_fixed_deadline`, `content_requirements` and `authority` - are **snapshotted onto the [IncidentNotification](incident-notification.md) row at creation** and are never rewritten by a later template edit. The `template` foreign key is `PROTECT`.

This is the same instinct as the existing `risks.Risk.criteria_snapshot` : a risk evaluated under the 2024 criteria must keep reading as it did in 2024, whatever the criteria say now. The regulatory case is stronger still. Suppose the 24-hour NIS2 early-warning template is corrected in March 2027 to cite a transposed national article instead of the directive. Without snapshotting, every obligation generated since 2025 would silently change its `obligation_reference` and its `content_requirements`, and a 2025 breach file printed for an inspector in 2027 would cite an article that did not exist when the filing was made. That is not a cosmetic defect : it is a fabricated record.

What the FK preserves that the snapshot cannot: **provenance**. `obligation.template` answers *which rule produced this*, and `obligation.template.history` answers *what did that rule say at the time*, through `django-simple-history`. The snapshot answers *what were we told we owed*. Both are needed, and neither substitutes for the other.

Fields **not** snapshotted, and why : `min_severity`, `requires_*`, `controller_roles`, `applicable_categories` and `jurisdiction_country` are matching inputs, not terms of the obligation. Once an obligation exists, the question *why does this exist* is answered by the template FK and by the incident's own recorded facts, both of which are historised.

## Lifecycle

`ReportingObligationTemplate` declares **no** `LIFECYCLE_NAME` and runs the core `default` lifecycle (`core/lifecycle.py` `DEFAULT_LIFECYCLE`). It is a governance statement about what the organisation believes it owes, and it needs a controlled approval rather than operational stages.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | Being written, typically against a freshly transposed text. Generates nothing. The only deletable step. |
| `pending` | Pending validation | `INTERMEDIATE` | no | no | no | `info` | Submitted for legal or DPO review |
| `validated` | Validated | `INTERMEDIATE` | **yes** | **yes** | no | `success` | **In force.** Only a template in this step generates obligations. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | Superseded : the regime changed, or the template was replaced by a more precise variant. Obligations it already generated are untouched. |

### Transitions

| Verb | Transition | `permission_action` | `requires_comment` |
|---|---|---|---|
| Submit | `draft -> pending` | `update` | no |
| Send back to draft | `pending -> draft` | `update` | no |
| Validate | `pending -> validated` | **`approve`** | no |
| Archive | `validated -> archived` | **`approve`** | no |

`permission_action="approve"` resolves against the overridden `workflow_perm_namespace`, so putting a legal template into force requires `incidents.response_plan.approve`. That gate is the point of running a lifecycle here at all : one careless edit to a `clock_hours` value changes every future deadline in the register.

### Why this entity needs no bookend correction

The lifecycles this module declares for itself must declare their `archived` step **explicitly** and hand-declare both bookend edges, because `lifecycle_from_state_flags()` auto-wires `ANY -> archived` and `archived -> draft` with **no `permission_action` and no `requires_comment`** (`core/lifecycle.py` `lifecycle_from_state_flags()`), and `user_can_perform()` allows any transition whose `permission_action` is empty : with a `deletable=True` draft step, that is an `archive -> restore -> delete` path around every gate.

The core `default` lifecycle has neither problem : its archive edge already carries `permission_action="approve"` and it declares **no restore transition at all**. This entity needs no bookend override, and one must not be added.

### Creation and the initial step

Every new template lands in `draft`, whatever the caller intended : `_ensure_initial_step()` snaps it there. A template that must arrive in force - the seeded set below, a customer import of a jurisdiction pack - is saved and then walked through the lifecycle inside one `transaction.atomic()` block:

```python
template = ReportingObligationTemplate(name="NIS2 early warning (24h) - ANSSI", ...)
template.save()
template.transition_to("pending", user, enforce_permission=False)
template.transition_to("validated", user, enforce_permission=False)
```

Writing `workflow_state="validated"` at insert would leave no `core.LifecycleEvent` rows, so a template that decides statutory deadlines would be in force with no record of anyone having approved it.

## The seeded template set

`scripts/seed_demo_data.py` ships the following templates in the `validated` step, created through the pattern above. They are demo data illustrating the mechanism for the Voltara Energy dataset, **not** a maintained regulatory database : an organisation writes and validates its own, which is exactly why this is a table and not a hard-coded matrix.

| Name | `regime` | `recipient_kind` | `authority` | `clock_anchor` | `clock_hours` | Conditions |
|---|---|---|---|---|---|---|
| GDPR breach notification (72h) - CNIL | `gdpr_art33_authority` | `supervisory_authority` | CNIL | `awareness_at` | 72 | `requires_personal_data`, `controller_roles = [controller, joint_controller]` |
| GDPR notification to the controller | `gdpr_art33_2_controller` | `controller` | (none) | `awareness_at` | (none, `no_fixed_deadline`) | `requires_personal_data`, `controller_roles = [processor]` |
| GDPR communication to data subjects | `gdpr_art34_data_subject` | `data_subject` | (none) | `awareness_at` | (none, `no_fixed_deadline`) | `requires_personal_data`, `requires_high_risk` |
| NIS2 early warning (24h) - ANSSI | `nis2_early_warning` | `csirt` | ANSSI | `awareness_at` | 24 | `requires_significant` |
| NIS2 incident notification (72h) - ANSSI | `nis2_notification` | `csirt` | ANSSI | `awareness_at` | 72 | `requires_significant` |
| NIS2 final report (1 month) - ANSSI | `nis2_final` | `csirt` | ANSSI | `previous_stage` | 720 | `requires_significant`, `depends_on_regime = nis2_notification` |
| NIS2 information to recipients | `nis2_recipients` | `customer` | (none) | `awareness_at` | (none, `no_fixed_deadline`) | `requires_significant` |

The NIS2 intermediate report (Art. 23(4)(c)) is deliberately **not** seeded : it is owed only when the authority asks for it, so it is created by hand with `source = manual` and `no_fixed_deadline = True` when the request arrives. Generating it speculatively would put a permanent open obligation on every significant incident and would train the operator to ignore the bucket.

The seeded set also demonstrates the `previous_stage` chain end to end : the final report's `due_at` is computed from the 72h notification's `first_submitted_at`, so it stays `NULL` until that filing is actually made, and appears the moment it is. A register that showed a final-report deadline one month after awareness would be wrong on every NIS2 incident, which is the concrete reason this anchor exists.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-19 | When triage produces **zero** obligations, `personal_data_involved` is `False` and `is_exercise` is `False`, a non-blank `Incident.no_obligation_justification` is mandatory. A template catalogue that is empty, unvalidated or too narrowly conditioned must never read as compliance on a green dashboard : the operator is made to say, in writing, that nothing is owed. |
| RG-INC-27 | `due_at` is recomputed in `save()` from the anchor plus `deadline_hours` **only** while `first_submitted_at` is null, and is never directly editable. Obligations generated from a `no_fixed_deadline` template carry `due_at = NULL`, are never counted late, and surface in a dedicated *no statutory deadline* bucket. |
| RG-INC-30 | Obligation terms generated from a template are **snapshotted** at creation and never rewritten by later template edits; the `template` FK is `PROTECT`. Generation only considers templates - and authorities - in a `reportable()` lifecycle state, never an `is_active` literal. |
| RG-INC-37 | Every picker, report, KPI, calendar feed and filter goes through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No lifecycle state literal for this entity appears outside `incidents/constants.py`. |
| RG-INC-39 | The template catalogue introduces **no** new permission feature : it is gated by `incidents.response_plan.*`. |

## Scope tenancy

`ReportingObligationTemplate` is a `BaseModel`, **not** a `ScopedModel` : a legal obligation is a property of the organisation and its jurisdiction, not of an ISMS scope, and `jurisdiction_country` already carries the only axis that genuinely varies. The catalogue is instance-wide, readable by any holder of `incidents.response_plan.read`.

The entity carries neither `scopes` nor `scope_parent_lookup`, so it is unaffected by the scope-inheritance fix phase 1 makes to `mcp/tools.py` `_filter_by_scopes`, `core/workflow_views.py` and `core/history_views.py` (see [Incident](incident.md#scope-tenancy)). Its viewset and its MCP registration set `scope_filtered = False` **explicitly**, so the choice reads as a decision rather than as the same omission that fix repairs. The obligations it generates are a different matter : [IncidentNotification](incident-notification.md) declares `scope_parent_lookup = "incident__scopes"` and depends on that fix.

## Endpoints

### REST

- `GET /api/v1/incidents/obligation-templates/` : list, filtered by `ReportingObligationTemplateFilter` (`status`, `regime`, `recipient_kind`, `authority_id`, `jurisdiction_country`, `min_severity`, `no_fixed_deadline`, `requires_significant`, `requires_personal_data`)
- `POST /api/v1/incidents/obligation-templates/` and `POST /api/v1/incidents/obligation-templates/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/obligation-templates/<uuid>/`
- `GET/POST /api/v1/incidents/obligation-templates/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`
- `GET /api/v1/incidents/obligation-templates/<uuid>/history/` : `core.history.build_timeline`

`ReportingObligationTemplateSerializer` / `...ListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at` and `version`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`, and `authority_name` as a read-only property-backed field. The viewset uses `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), with `permission_feature = "response_plan"`.

There is deliberately **no** "generate obligations" API action. Generation is a side effect of the incident's own transitions and of the two events listed above; exposing it as a callable endpoint would let a caller create legal obligations out of band, with no lifecycle event on the incident to explain where they came from.

### MCP

- `_register_crud(server, "obligation_template", ReportingObligationTemplate, "incidents.response_plan", scope_filtered=False, ...)` generates `list_obligation_templates`, `get_obligation_template`, `create_obligation_template`, `batch_create_obligation_templates`, `update_obligation_template`, `delete_obligation_template`, `transition_obligation_template`, `obligation_template_allowed_transitions`, `get_obligation_template_history`.
- Filters : `status`, `regime`, `recipient_kind`, `authority_id`, `jurisdiction_country`. Search fields : `reference`, `name`, `legal_reference`.
- `regime`, `recipient_kind`, `clock_anchor`, `depends_on_regime`, `min_severity` and the three JSON list fields each get an explicit `enum` entry in `field_overrides`; `content_requirements` uses `_html_field()`; `authority_id` carries the description `Use list_reporting_authorities to get valid IDs`.

`mcp/tools.py` `HELP_TEXT` gains `ReportingObligationTemplate=ROBT` in the reference-prefix block, and the `TOPIC_INCIDENTS` help topic gains a section for this entity listing its writable fields, its enum values, its filters and its reference prefix.

## Permissions

| Codename | Description |
|---|---|
| `incidents.response_plan.read` | List and read templates |
| `incidents.response_plan.create` | Add a template |
| `incidents.response_plan.update` | Edit a template, submit it for validation, send it back to draft |
| `incidents.response_plan.approve` | **Put a template into force** (validate) and archive it |
| `incidents.response_plan.delete` | Delete a `draft` template |

## UI

- **List** (`/incidents/obligation-templates/`) : the house list stack, grouped by `regime` and ordered by `order` then `name`, in the module's configuration area. Columns : name, regime, recipient kind, authority, the clock rendered as a single human string (`24 h from legal awareness`, `1 month from the previous filing`, `No statutory deadline`), the conditions as a row of small badges, and the state badge. Predefined filters : *In force*, *Draft*, *No statutory deadline*, one per regime family (GDPR, NIS2, DORA, contractual).
- **Detail** (`/incidents/obligation-templates/<uuid>/`) : strict 2-column card layout, no nav-tabs. Left column : *Obligation* (regime, recipient kind, legal reference, authority with a link to its [catalogue entry](reporting-authority.md)); *Clock* (anchor, hours, `no_fixed_deadline`, `depends_on_regime`, rendered as one sentence in plain language above the raw fields); *Trigger conditions* (every condition listed, with the ones that are **not** set shown as *any* rather than omitted, so the reader can tell a deliberate blank from a forgotten one); *Content requirements* (the HTML checklist, full width, exactly as it will appear next to the drafting field). Right column, sticky : `{% workflow_badge %}`, `order`, a count of obligations generated from this template with a link to the filtered obligation list, tags, and the history trigger.
- **The clock sentence is the most important string on the page.** `24 h from legal awareness (awareness_at)` and `1 month from the filing of the NIS2 incident notification` are what a reviewer actually checks; a table of five raw fields is what they skip. Both are rendered, in that order.
- Create and update use `HtmxFormMixin` drawer modals. The condition block has many checkboxes and three multi-selects (`controller_roles`, `applicable_categories`, `additional_regimes` on the authority side), so it gets explicit mobile-first attention : stacked labels, no horizontal scrolling, and a sticky action bar that does not cover the last field.
- Both themes are checked. The condition badges use the neutral navy identity colour, **not** semantic status colours : per the brand guidelines, semantic colours are reserved for statuses, and a trigger condition is not a status.

## Translations

Several of this entity's labels collide with `msgid`s already present in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

**Enum labels, field verbose names and template strings** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`:

| String | Existing bare entry | Action |
|---|---|---|
| "Required" (the *Required* condition badge, and the `required` decision label reused in the generated-obligations card) | `django.po` -> "Requis" | `{% trans "Required" context "incident" %}` |
| "Incident" (the incident category filter label on the generated-obligations card) | `django.po` -> "Incident" | `{% trans "Incident" context "incident" %}` |
| "Severity" (`min_severity` verbose name) | already present as a bare entry | `pgettext_lazy("incident", "Minimum severity")` avoids the collision outright, and reads better |
| "Other" (any `ThreatCategory` or regime label rendered in the condition badges) | `django.po` -> "Autre" | `pgettext_lazy("incident", "Other")` |

Two labels are **reused deliberately** rather than re-declared : "Jurisdiction" (`django.po` -> "Juridiction") and "Order" (`django.po` -> "Ordre") already carry the right French, so both fields use the bare `gettext_lazy` form and add no `.po` entry. Every other label on this entity ("Regime", "Recipient kind", "Legal reference", "Clock anchor", "Clock hours", "No statutory deadline", "Depends on regime", "Content requirements", "Controller roles", "Applicable categories") is a new, non-colliding bare `msgid`.

**Step and transition labels must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` carried in code is lost after the `post_migrate` DB round-trip and the label resolves to whatever the bare `msgid` maps to. This entity is safe by construction : it runs the core `default` lifecycle and declares no step or transition label of its own.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- GDPR Art. 33(1)-(2) (notification to the authority and by a processor to the controller), Art. 34(1) and 34(3)(a)-(c) (communication to data subjects and its exemptions)
- NIS2 Art. 23(3) (significance) and Art. 23(4)(a)-(d) (24h early warning, 72h notification, intermediate report on request, final report within one month **of the notification**)
- NIS2 Art. 23(1) (informing the recipients of the service)
- DORA Art. 19 (initial, intermediate and final major ICT incident reports), whose RTS timings are expressible with the same fields
- ePrivacy Directive Art. 4(3) and Cyber Resilience Act Art. 14 : expressible with this template shape, not shipped as defaults
- [ReportingAuthority](reporting-authority.md) : the body a template files with, and the `reportable()` gate it shares
- [IncidentNotification](incident-notification.md) : the obligation instance a template generates, and where the snapshot lands
- [PersonalDataBreach](personal-data-breach.md) : supplies `controller_role` and `high_risk_to_rights` to conditions 8 and 10
- [Incident](incident.md) : supplies `severity`, `category`, `personal_data_involved`, `is_significant` and the two new cross-border / malicious-act verdicts
- [IncidentResponsePlan](incident-response-plan.md) : the phase-1 `applicable_regimes` list this catalogue supersedes at runtime
- [README.md](README.md) : module business rules, permissions, notifications
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework this entity plugs into

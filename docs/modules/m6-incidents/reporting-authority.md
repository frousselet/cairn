# ReportingAuthority

`incidents.models.reporting_authority.ReportingAuthority`

The catalogue of the bodies an incident can owe something to : supervisory authorities (CNIL), CSIRTs and competent authorities (ANSSI), sector and financial regulators, law enforcement. One row per body, holding the **filing channel and the filing procedure**, so that an operator working a 24-hour NIS2 clock or a 72-hour GDPR clock is reading a portal URL and a procedure the organisation wrote in advance, rather than searching a regulator's website at 02:00 with a lawyer on the phone.

The entity is deliberately small. It answers three questions and no others : *who is this body, how do we file with it, and is this row trustworthy enough to generate obligations from.* Everything about **what** is owed lives on [ReportingObligationTemplate](reporting-obligation-template.md), and everything about a **particular** filing lives on [IncidentNotification](incident-notification.md) and [NotificationFiling](notification-filing.md).

File: `incidents/models/reporting_authority.py`

Phase **2**. `BaseModel` subclass : UUID PK, sequential `reference` (prefix **`RGAU`**, e.g. `RGAU-1`), `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the core **`default` 4-state lifecycle**. `workflow_perm_namespace` is overridden to `incidents.response_plan` : the default `app_label.model_name` would spell `incidents.reportingauthority`, which matches no feature in `PERMISSION_REGISTRY`, and every transition would then be refused for everyone. Phase 2 introduces **no new permission feature** (RG-INC-39) : the authority catalogue is module configuration, and it is governed by the same codenames as the [IncidentResponsePlan](incident-response-plan.md).

## Why a catalogue instead of a free-text recipient

[IncidentNotification](incident-notification.md) can always name a recipient in free text (`recipient_name`), and for a one-off contractual notification that is the right answer. An authority is different in three ways that a free-text string cannot carry:

- **It is reused.** The same body receives every GDPR filing the organisation ever makes. Retyping "Commission Nationale de l'Informatique et des Libertés" on each incident guarantees three spellings in the register within a year, and an incident register that cannot be grouped by recipient cannot answer *how many times did we file with the CNIL last year*.
- **It carries operational payload.** `portal_url`, `contact_email`, `contact_phone`, `notification_language` and `procedure` are exactly the fields nobody has time to look up during the incident. Preparing them is part of A.5.24 planning, not part of the response.
- **It is a governed statement.** A portal URL that has changed, or a procedure that describes a decommissioned form, is worse than no catalogue at all. Running the `default` lifecycle means a row must be **validated** before obligation generation will consider it, and a stale row is `archived` rather than silently edited into a different body.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `RGAU-N`, unique | Business reference |
| `name` | string | required, max 255 | Full legal name of the authority, e.g. `Commission Nationale de l'Informatique et des Libertés` |
| `short_name` | string | optional, max 50, blank default | Common acronym : `CNIL`, `ANSSI`, `ACPR`, `BSI`. What the list view and every badge actually display. |
| `authority_type` | enum | required, default `other` | `AuthorityType` : what kind of body this is. Drives the icon and the default `recipient_kind` proposed when a template is created against this row. |
| `primary_regime` | enum | required | `NotificationRegime` (declared in `incidents/constants.py`, shared with [IncidentNotification](incident-notification.md)). The regime this body principally acts under. A filtering and display aid only : obligation matching keys off the **template's** `regime`, never off this field. |
| `additional_regimes` | JSON | optional, `default=list` | Other regimes the same body handles. `JSONField`, not `ArrayField`, so `core.settings_test` (SQLite in memory) runs the module unchanged. Values are `NotificationRegime` codes, validated in `clean()`. |
| `jurisdiction_country` | string | optional, max 100, blank default | Country name, ISO code or the literal `EU`. Used to select the right national authority when generating obligations from a template that restricts `jurisdiction_country`. Blank means *not jurisdiction-specific*. |
| `portal_url` | URL | optional, blank default | The online notification portal. Rendered as the primary action on the notification detail page : one click from the obligation to the form that discharges it. |
| `contact_email` | email | optional, blank default | Notification mailbox, for regimes filed by email rather than through a portal |
| `contact_phone` | string | optional, max 50, blank default | Emergency line. Several CSIRTs expect a phone call before the written filing, and that fact belongs in the register rather than in someone's memory. |
| `notification_language` | string | optional, max 10, blank default | Language the filing must be in (e.g. `fr`, `en`, `de`). A filing rejected for language is a filing not made, and the clock does not stop. |
| `procedure` | text | optional, HTML | The filing procedure : which form, which attachments, who signs, what the acknowledgement looks like, what the escalation path is when the portal is down. This is the field that earns the entity its place. |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (core `default`) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

### Relations

`ReportingAuthority` declares no outgoing relation of its own. It is pointed at from three places:

| Reverse accessor | Source | Type | Description |
|---|---|---|---|
| `obligation_templates` | [ReportingObligationTemplate](reporting-obligation-template.md) `.authority` | FK, `PROTECT`, optional | The generation rules that name this body. `PROTECT` : an authority with templates cannot be deleted. |
| `obligations` | [IncidentNotification](incident-notification.md) `.authority` | FK, `PROTECT`, optional | Every obligation ever generated against this body. `PROTECT` : deleting an authority that a two-year-old breach file cites would make the file unreadable. |
| `lead_breaches` | [PersonalDataBreach](personal-data-breach.md) `.lead_authority` | FK, `SET_NULL`, optional | The lead supervisory authority under GDPR Art. 56 (one-stop-shop) |

The asymmetry is deliberate : the two `PROTECT` edges are the ones an audit file depends on, and `SET_NULL` on `lead_authority` keeps a breach record readable if a one-stop-shop determination is later withdrawn.

### Meta

- `ordering = ["name"]`
- `UniqueConstraint(["name", "jurisdiction_country"], name="unique_authority_per_jurisdiction")`

The unique constraint is per jurisdiction on purpose : *Data Protection Authority* is a defensible `name` in a dozen countries, and a group operating in several of them needs one row each. Both columns are non-nullable (`jurisdiction_country` is `blank=True, default=""`, never `NULL`), so the constraint behaves identically on PostgreSQL and on SQLite : there is no `NULL`-distinctness surprise of the kind that makes a unique index over nullable columns silently permit duplicates.

## Enumerations

### AuthorityType

| Value | Label |
|---|---|
| `supervisory_authority` | Supervisory authority |
| `csirt` | CSIRT |
| `competent_authority` | Competent authority |
| `sector_regulator` | Sector regulator |
| `financial_regulator` | Financial regulator |
| `law_enforcement` | Law enforcement |
| `other` | Other |

A single body frequently wears two of these hats : ANSSI is both the French **competent authority** and the national **CSIRT** under NIS2. The catalogue does not model that as two rows. `authority_type` records the principal capacity, `primary_regime` and `additional_regimes` record what the body actually handles, and the [templates](reporting-obligation-template.md) decide which capacity is engaged for a given filing.

`NotificationRegime` and `NotificationRecipientKind` are declared once in `incidents/constants.py` and documented on [IncidentNotification](incident-notification.md). They are not repeated here.

## Lifecycle

`ReportingAuthority` declares **no** `LIFECYCLE_NAME` and runs the core `default` lifecycle (`core/lifecycle.py` `DEFAULT_LIFECYCLE`). A catalogue row is a governance statement, not an operational object : it needs a controlled approval, not stages.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | Being researched. Not offered to any picker, and generates nothing. The only deletable step. |
| `pending` | Pending validation | `INTERMEDIATE` | no | no | no | `info` | Submitted for review, typically by the DPO or the CISO |
| `validated` | Validated | `INTERMEDIATE` | **yes** | **yes** | no | `success` | **Usable.** Only a row in this step is offered in the authority picker and considered by obligation generation. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | Superseded : the body was renamed, merged, or its filing channel replaced. Existing obligations keep pointing at it. |

### Transitions

| Verb | Transition | `permission_action` | `requires_comment` |
|---|---|---|---|
| Submit | `draft -> pending` | `update` | no |
| Send back to draft | `pending -> draft` | `update` | no |
| Validate | `pending -> validated` | **`approve`** | no |
| Archive | `validated -> archived` | **`approve`** | no |

`permission_action="approve"` resolves against the overridden `workflow_perm_namespace`, so validating an authority requires `incidents.response_plan.approve`.

### Why this entity needs no bookend correction

The lifecycles this module declares for itself have to declare their `archived` step **explicitly** and hand-declare both bookend edges, because `lifecycle_from_state_flags()` auto-wires `ANY -> archived` and `archived -> draft` with **no `permission_action` and no `requires_comment`** (`core/lifecycle.py` `lifecycle_from_state_flags()`), and `user_can_perform()` allows any transition whose `permission_action` is empty : combined with a `deletable=True` draft step, that is an `archive -> restore -> delete` path around every governance gate.

The core `default` lifecycle has neither problem. Its archive edge already carries `permission_action="approve"`, and it declares **no restore transition at all**, so there is no path from `validated` back into a deletable step. This entity therefore needs no `transition_to()` bookend override, and one must not be added.

### Creation and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`), and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. **Every new row lands in `draft`**, including one created by the demo seed, by the REST API or by MCP. No row in this module is ever "created in" a domain step.

An authority that must arrive already usable - the seeded CNIL and ANSSI rows, a customer import of a national catalogue - is saved and then walked through the lifecycle inside one `transaction.atomic()` block:

```python
authority = ReportingAuthority(name="...", primary_regime="gdpr_art33_authority", ...)
authority.save()
authority.transition_to("pending", user, enforce_permission=False)
authority.transition_to("validated", user, enforce_permission=False)
```

Assigning `workflow_state="validated"` at insert would stick, because `_ensure_initial_step()` only snaps a blank or unknown value, but it would leave **no `core.LifecycleEvent` rows** : the catalogue would claim a validated legal contact that nobody is recorded as having validated.

## Seeded authorities

`scripts/seed_demo_data.py` ships two rows in the `validated` step, created through the pattern above:

| Field | CNIL | ANSSI |
|---|---|---|
| `name` | Commission Nationale de l'Informatique et des Libertés | Agence Nationale de la Sécurité des Systèmes d'Information |
| `short_name` | CNIL | ANSSI |
| `authority_type` | `supervisory_authority` | `competent_authority` |
| `primary_regime` | `gdpr_art33_authority` | `nis2_notification` |
| `additional_regimes` | `["gdpr_art34_data_subject", "eprivacy"]` | `["nis2_early_warning", "nis2_intermediate", "nis2_final", "cert_csirt"]` |
| `jurisdiction_country` | France | France |
| `portal_url` | the CNIL breach-notification portal | the ANSSI incident-reporting portal |
| `notification_language` | `fr` | `fr` |
| `procedure` | Which form, which attachments, who signs, what the acknowledgement looks like | The same, plus the CSIRT phone escalation |

They exist so the demo dataset (Voltara Energy) exercises the full obligation chain and so the module's screenshots show a real portal link rather than an empty card. They are demo data, not a shipped regulatory database : the module makes **no** claim to maintain a European authority directory, and an organisation outside France writes its own rows. Portal URLs are recorded as data precisely because they change, and a stale row is corrected by an ordinary edit that `HistoricalRecords` captures.

## Obligation generation

Generation is described in full on [ReportingObligationTemplate](reporting-obligation-template.md). The one rule that belongs here:

> **Only authorities in a `reportable()` lifecycle state are considered** (RG-INC-30). The generator filters on `workflow_state__in=reportable("default")`, never on an `is_active` boolean and never on a state literal (RG-INC-37). A `draft` authority is a work in progress, not a legal contact, and generating a 24-hour obligation against a portal URL nobody has checked is worse than generating nothing, because the dashboard then reads green.

When a template names an authority that has since been archived, generation still succeeds and still cites the archived row : the obligation snapshots the authority's identity along with the rest of the legal terms, and the `PROTECT` foreign key keeps the row readable. What the archived state prevents is the creation of **new** templates against it and the appearance of the row in the authority picker.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-30 | Obligation generation only considers `ReportingAuthority` and [ReportingObligationTemplate](reporting-obligation-template.md) rows in a `reportable()` lifecycle state, never an `is_active` literal. The authority's identity and filing channel are **snapshotted** onto each generated obligation, so a later catalogue edit cannot rewrite a two-year-old file. |
| RG-INC-37 | Every picker, report, KPI and filter goes through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No lifecycle state literal for this entity appears outside `incidents/constants.py`. |
| RG-INC-39 | The catalogue introduces **no** new permission feature. It is gated by `incidents.response_plan.*`, the module's configuration feature, which keeps the module at exactly six features and thirty codenames for its whole life. |

## Scope tenancy

`ReportingAuthority` is a `BaseModel`, **not** a `ScopedModel`, and this is deliberate : the CNIL is the CNIL for every scope of the ISMS, and a per-scope authority catalogue would produce one duplicate row per subsidiary with no benefit. The catalogue is therefore instance-wide, readable by any holder of `incidents.response_plan.read` and writable by any holder of `incidents.response_plan.update`.

Because the entity carries neither `scopes` nor `scope_parent_lookup`, it is unaffected by the scope-inheritance fix that phase 1 makes to `mcp/tools.py` `_filter_by_scopes`, `core/workflow_views.py` and `core/history_views.py` (see [Incident](incident.md#scope-tenancy)). Its viewset and its MCP registration set `scope_filtered = False` **explicitly** rather than inheriting it by omission, so the choice is visible in code review instead of looking like the same oversight that fix repairs.

## Endpoints

### REST

- `GET /api/v1/incidents/reporting-authorities/` : list, filtered by `ReportingAuthorityFilter` (`status`, `authority_type`, `primary_regime`, `jurisdiction_country`)
- `POST /api/v1/incidents/reporting-authorities/` and `POST /api/v1/incidents/reporting-authorities/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/reporting-authorities/<uuid>/`
- `GET/POST /api/v1/incidents/reporting-authorities/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`
- `GET /api/v1/incidents/reporting-authorities/<uuid>/history/` : `core.history.build_timeline`

`ReportingAuthoritySerializer` / `ReportingAuthorityListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at` and `version`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`. The viewset uses `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), following `trust_center/api/views.py` `_ManagedViewSet`, with `permission_feature = "response_plan"`.

### MCP

- `_register_crud(server, "reporting_authority", ReportingAuthority, "incidents.response_plan", scope_filtered=False, ...)` generates `list_reporting_authorities`, `get_reporting_authority`, `create_reporting_authority`, `batch_create_reporting_authorities`, `update_reporting_authority`, `delete_reporting_authority`, `transition_reporting_authority`, `reporting_authority_allowed_transitions`, `get_reporting_authority_history`.
- Filters : `status`, `authority_type`, `primary_regime`, `jurisdiction_country`. Search fields : `reference`, `name`, `short_name`.
- `authority_type`, `primary_regime` and the `additional_regimes` list each get an explicit `enum` entry in `field_overrides`; `procedure` uses `_html_field()`.

`mcp/tools.py` `HELP_TEXT` gains `ReportingAuthority=RGAU` in the reference-prefix block. Do not copy the neighbouring lines when adding it : the `Indicator=INDI` entry already mis-states the prefix (the model says `INDC`) and the `ActionPlan=ACTPL` (the model says `CAPL`).

## Permissions

| Codename | Description |
|---|---|
| `incidents.response_plan.read` | List and read the authority catalogue |
| `incidents.response_plan.create` | Add an authority |
| `incidents.response_plan.update` | Edit an authority, submit it for validation, send it back to draft |
| `incidents.response_plan.approve` | Validate an authority (make it usable for generation) and archive it |
| `incidents.response_plan.delete` | Delete a `draft` authority |

Under the six `SYSTEM_GROUPS` suffix filters, Super Administrateur and Administrateur get everything; RSSI and DPO get read / create / update / approve, which is the correct set for the people who actually maintain a regulatory contact list; Contributeur gets read / create / update; Auditeur and Lecteur get read.

## UI

- **List** (`/incidents/reporting-authorities/`) : the house list stack, sorted by `name`, with predefined filters for *Validated*, *Draft* and one per `authority_type`. Columns : short name, full name, type, primary regime, jurisdiction, state badge. The list lives in the module's configuration area alongside [IncidentResponsePlan](incident-response-plan.md) and [ReportingObligationTemplate](reporting-obligation-template.md), not in the operational incident navigation, because nobody edits a catalogue during a response.
- **Detail** (`/incidents/reporting-authorities/<uuid>/`) : strict 2-column card layout, no nav-tabs. Left column : *Identity* (name, short name, type, jurisdiction, primary and additional regimes); *Filing channel* (portal URL rendered as a prominent external-link button, contact email, phone, notification language); *Procedure* (the HTML field, full width). Right column, sticky : `{% workflow_badge %}`, the obligation templates that name this body, a count of obligations ever generated against it, tags, and the history trigger.
- **Where it is actually used** : the [IncidentNotification](incident-notification.md) detail page renders this row's `portal_url`, `contact_email`, `notification_language` and `procedure` directly beside the drafting field, with the countdown to `due_at` above them. That is the screen the whole entity exists to populate, and it must be checked at mobile width : an operator filing from a phone at 02:00 is a real scenario, and the portal button must be reachable without horizontal scrolling.
- Create and update use `HtmxFormMixin` drawer modals. Both themes are checked : the external-link button and the state badge are the two components most likely to fail contrast in dark mode.

## Translations

Two of this entity's labels collide with `msgid`s already present in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

**Enum labels, field verbose names and template strings** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`:

| String | Existing bare entry | Action |
|---|---|---|
| `AuthorityType.OTHER` "Other" | `django.po` -> "Autre" | `pgettext_lazy("incident", "Other")` |
| `contact_email` verbose name "Email" | `django.po` -> "Email" | Label the field "Contact email", which does not collide; if the shorter label is wanted, `pgettext_lazy("incident", "Email")` |

Two labels are **reused deliberately** rather than re-declared : "Jurisdiction" (`django.po` -> "Juridiction") and "Country" (`django.po` -> "Pays") already carry the right French, so `jurisdiction_country` uses the bare `gettext_lazy` form and adds no `.po` entry. Every other label on this entity ("Short name", "Authority type", "Primary regime", "Additional regimes", "Portal URL", "Contact phone", "Notification language", "Procedure") is a new, non-colliding bare `msgid`.

**Step and transition labels must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` carried in code is lost after the `post_migrate` DB round-trip and the label then resolves to whatever the bare `msgid` maps to. This entity is safe by construction : it runs the core `default` lifecycle and declares no step or transition label of its own. "Draft" (`django.po` -> "Brouillon") and "Archived" (`django.po` -> "Archivé") are the core labels, with the correct French already in place.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- GDPR Art. 33(1) (notification to the supervisory authority), Art. 55-56 (competence and the one-stop-shop lead authority)
- NIS2 Art. 23 (reporting obligations to the CSIRT or the competent authority)
- DORA Art. 19 (reporting of major ICT-related incidents to the competent authority)
- ISO/IEC 27001:2022 A.5.24 : preparing the filing channels **before** an incident is part of planning, not of response
- ISO/IEC 27001:2022 A.5.5 (contact with authorities) : this catalogue is the documented evidence for that control
- [ReportingObligationTemplate](reporting-obligation-template.md) : the rule that decides which authority is owed what, and when
- [IncidentNotification](incident-notification.md) : the obligation instance, which snapshots this row's terms
- [PersonalDataBreach](personal-data-breach.md) : `lead_authority` under GDPR Art. 56
- [IncidentResponsePlan](incident-response-plan.md) : shares the `incidents.response_plan` permission feature and the same governance posture
- [README.md](README.md) : module business rules, permissions, notifications
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework this entity plugs into

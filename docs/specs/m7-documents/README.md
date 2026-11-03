# Module 7 : Documents

## Functional and technical specification

The register of the organisation's **documented information** (ISO/IEC 27001:2022 clause 7.5) : the information security policy (clause 5.2), the topic-specific policies (A.5.1), and the procedures, standards and charters that implement them. It answers the four questions an auditor asks of every governing document : *which version is in force, who approved it and when, when is it next reviewed, and who has acknowledged it.*

**Status : proposed for v0.37.0, not yet implemented.**

## Entities

| Entity | Class | Reference prefix | Lifecycle |
| --- | --- | --- | --- |
| [Policy](policy.md) | `documents.models.policy.Policy` | `PLCY` | `policy` |
| [PolicyVersion](policy-version.md) | `documents.models.policy_version.PolicyVersion` | `PLVR` | `policy_version` |
| [AcknowledgementCampaign](acknowledgement-campaign.md) | `documents.models.campaign.AcknowledgementCampaign` | `ACKC` | `acknowledgement_campaign` |
| [PolicyAcknowledgement](policy-acknowledgement.md) | `documents.models.acknowledgement.PolicyAcknowledgement` | none | none (write-once record) |

---

## 1. Overview

### 1.1 Purpose

Today a Cairn instance can tell an auditor what its risks, controls and incidents are, but not what its **policies** say, which version applies, or whether staff were told. The policy text lives in a shared drive, its approval in an email, its review date in someone's head, and the evidence of acknowledgement in a spreadsheet. The management review spec already anticipates the gap : `IsmsChange.affected_policies` is free text "until a `Policy` model exists".

This module makes the policy set a governed register :

- a **document** has an identity (reference, title, type, owner, review cycle, scopes, the requirements it answers) and a series of **versions**;
- each **version** is frozen once submitted, approved through its lifecycle, and only one version of a document is **in force** at a time; earlier versions stay readable as superseded records (clause 7.5.3 retention of obsolete documented information);
- the content is the **rich text** of the policy in Cairn, an attached **PDF** (the signed copy), or both;
- **acknowledgement campaigns** ask a defined audience to confirm they have read a given version, and record each confirmation as a write-once row (A.5.1 "communicated to and acknowledged by relevant personnel", clause 7.3 awareness);
- a document can be **published on the Trust Center**, always serving its version in force;
- the **management review** links ISMS changes to the documents they affect and lists the documents due for review.

### 1.2 Functional scope

| Area | In v0.37.0 |
| --- | --- |
| Document register with types, owner, approver, review cycle, scopes, tags, requirement links, parent / child structure (a policy and the procedures under it) | yes |
| Versions with frozen content (rich text and / or PDF), change summary, approval, single version in force, automatic supersession | yes |
| "New version" from the version in force (copies the content into a new draft) | yes |
| Review cycle : next review date, calendar entries, dashboard widget, reminders, overdue flag | yes |
| Acknowledgement campaigns over users, groups and roles; personal "To acknowledge" list; reminders; completion rate | yes |
| Management review : `IsmsChange.affected_documents` link and a "Documents due for review" card on the review | yes |
| Trust Center : a `TrustCenterDocument` sourced from a policy, serving its version in force | yes |
| REST API, MCP tools, global search, kanban (personal acknowledgements), predefined indicators, help banners, demo seed | yes |
| Side-by-side diff between two versions | no (see §11) |
| Policy exceptions / waivers register | no (see §11) |
| Electronic signature of a version | no (see §11) |

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
| --- | --- |
| Accounts | `User` for owners, approvers, authors and acknowledgers; `Group` as a campaign audience; `accounts.Notification` for every notification (no new notification model); `PERMISSION_REGISTRY` and `SYSTEM_GROUPS`. |
| Context | `ScopedModel` / `BaseModel`, `Scope` tenancy, `Tag`, `Role` (`Role.assigned_users`) as a campaign audience. |
| Compliance | `Requirement` : `Policy.linked_requirements` (A.5.1, clause 5.2, and any requirement a document answers). The requirement detail page lists the documents linked to it. |
| Management review | `IsmsChange.affected_documents` (M2M -> `Policy`); the review detail page lists documents whose next review falls in the review period. |
| Trust Center | `TrustCenterDocument.policy` as a third, mutually exclusive document source (see [Trust Center document](../m5-trust-center/document.md)). |
| Reports | The WeasyPrint pipeline renders a version's rich text to PDF when no PDF is attached (Trust Center download, version export). |

---

## 2. Business rules : the RG-DOC register

### 2.1 Documents and versions

| ID | Rule |
| --- | --- |
| RG-DOC-01 | A [Policy](policy.md) has **at most one** [PolicyVersion](policy-version.md) in the `in_force` step. Putting a version in force moves the previous in-force version of the same document to `superseded` in the **same transaction**, through a recorded lifecycle transition (a `core.LifecycleEvent` with the acting user and the comment "Superseded by PLVR-n"), never by writing `workflow_state`. |
| RG-DOC-02 | A version's content (`content`, the PDF, `version_label`, `change_summary`) is **editable only in `draft`**. From `in_review` onward it is frozen : the update form, the REST `PUT` / `PATCH` and the MCP `update_policy_version` refuse any change to these fields. Sending a version back to draft re-opens it. |
| RG-DOC-03 | A version has a content : rich text, a PDF, or both. Submitting a version with neither is refused. |
| RG-DOC-04 | The attached PDF follows the contract rules (RG-CTR-02) : `.pdf` extension, `%PDF-` magic bytes, at most 25 MB, stored inline (`file_content`), served only through the permission-checked, scope-filtered download view, excluded from history and never serialized. A SHA-256 of the bytes is stored with it, so a downloaded copy can be checked against the approved one. |
| RG-DOC-05 | `version_label` is unique per document. The "New version" action proposes the next label (minor bump `1.2 -> 1.3`, or major `1.2 -> 2.0`), copies the in-force content and PDF into a new draft, and leaves `change_summary` empty. |
| RG-DOC-06 | From the second version of a document, `change_summary` is required to submit : a reviewer must know what changed. |
| RG-DOC-07 | Approval stamps `approved_by` and `approved_at` from the transition itself (the acting user, now). Neither field is editable on any surface. `effective_from` defaults to the approval date; it can be set earlier (retroactive formalisation of a practice) but never in the future in v0.37.0 (see §11). |
| RG-DOC-08 | A document's identity (title, type, owner, scopes, requirement links, review cycle) stays editable while it is `active`; those edits are history-tracked and do not create a version. The **content** only changes through a new version. |
| RG-DOC-09 | A document can be put `active` only when it has a version in force, and is `retired` (archived) only with a comment. Retiring a document supersedes its in-force version in the same transaction (RG-DOC-01 mechanics) and closes its open campaigns. |
| RG-DOC-10 | `parent` builds the document tree (a policy and the procedures implementing it). A document cannot be its own ancestor; the depth is not limited. Retiring a parent does not retire its children, but the parent's detail page and the children's pages flag the situation. |

### 2.2 Review cycle

| ID | Rule |
| --- | --- |
| RG-DOC-11 | `next_review_date` is **derived** : the in-force version's `effective_from` plus `review_frequency_months`, unless the owner has set an explicit `next_review_override`. It is stored (indexed, for the calendar and the dashboard) and recomputed on every version transition and every save of the document. |
| RG-DOC-12 | A document is **overdue for review** when `next_review_date < today` and it is `active`. Overdue is always derived, never a lifecycle step. Putting a new version in force, or recording a review without change (RG-DOC-13), clears it. |
| RG-DOC-13 | "Reviewed, no change" is a recorded act : a `Policy.record_review(user, comment)` method that stamps `last_reviewed_at` / `last_reviewed_by` and recomputes `next_review_date` from the review date, with a history entry. It is how an owner closes a review cycle without issuing a new version. Requires `documents.policy.approve`. |

### 2.3 Acknowledgement

| ID | Rule |
| --- | --- |
| RG-DOC-14 | A [campaign](acknowledgement-campaign.md) targets **one version**, which must be `in_force` when the campaign is launched. |
| RG-DOC-15 | The audience is the union of the selected users, the members of the selected groups and the users assigned to the selected roles, active users only, de-duplicated. It is **resolved once, at launch** : one [PolicyAcknowledgement](policy-acknowledgement.md) row per person, in `pending`. A later change to a group does not silently change who was asked; "Add newcomers" re-resolves the audience on demand and creates the missing rows, recorded in the campaign history. |
| RG-DOC-16 | An acknowledgement is **write-once** : `acknowledged_at` is stamped by the acknowledging user's own action, with the statement text they confirmed snapshotted on the row. It can never be edited, reassigned or deleted on any surface; an acknowledgement given in error is cancelled only by archiving the whole campaign, which keeps every row. |
| RG-DOC-17 | Only the person a row belongs to can acknowledge it. No permission is required for that act beyond being the addressee; an administrator cannot acknowledge on someone's behalf. |
| RG-DOC-18 | When the version a campaign targets is superseded, the campaign is closed in the same transaction and its pending rows become `expired`; the completion rate is frozen. A campaign for the new version is a new campaign. |
| RG-DOC-19 | Completion rate = acknowledged rows / (all rows - excused rows). An owner may **excuse** a pending row (leaver, long absence) with a mandatory reason; the row keeps its history. |

### 2.4 Integration

| ID | Rule |
| --- | --- |
| RG-DOC-20 | Every report, KPI, calendar feed and picker filters through `reportable()` / `linkable()` / `linkable_or_linked()`. The `affected_documents` picker on an ISMS change and the `policy` picker on a Trust Center document offer `linkable()` documents (`active`), keeping existing links to a since-retired document. |
| RG-DOC-21 | A Trust Center document sourced from a policy serves the document's **current** in-force version : its PDF when one is attached, otherwise the rich text rendered to PDF. When the document has no version in force or is retired, the Trust Center entry disappears from the public page automatically (the RG-TC-08 second gate). |
| RG-DOC-22 | `Policy` and `AcknowledgementCampaign` are `ScopedModel`s and carry their own `scopes`; `PolicyVersion` and `PolicyAcknowledgement` inherit their parent's scopes through `scope_parent_lookup` (`policy__scopes`, `campaign__policy_version__policy__scopes`) in `ScopeFilterMixin`, the API mixin and the MCP scope filter. A user's own pending acknowledgements are visible to them regardless of their scopes. |

---

## 3. Lifecycles

Each lifecycle is generated from its transition constants in `documents/constants.py` and registered in `documents/lifecycles.py`, imported from `DocumentsConfig.ready()`. A test asserts each model's `get_lifecycle().name`, because an un-imported lifecycle silently falls back to the core 4-state one.

### 3.1 `policy` (the document)

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Draft | DRAFT | no | no | **yes** | neutral |
| `active` | Active | INTERMEDIATE | **yes** | **yes** | no | success |
| `retired` | Retired | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Gate |
| --- | --- | --- | --- | --- |
| Activate | `draft -> active` | `approve` | no | a version in force (RG-DOC-09) |
| Retire | `active -> retired` | `approve` | **yes** | supersedes the version in force, closes open campaigns |
| Retire | `draft -> retired` | `update` | **yes** | |

No restore edge : a retired document is a closed record. Re-issuing it is a new document.

### 3.2 `policy_version`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Draft | DRAFT | no | no | **yes** | neutral |
| `in_review` | In review | INTERMEDIATE | no | no | no | info |
| `in_force` | In force | INTERMEDIATE | **yes** | **yes** | no | success |
| `superseded` | Superseded | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Side effect |
| --- | --- | --- | --- | --- |
| Submit for review | `draft -> in_review` | `update` | no | RG-DOC-03 / RG-DOC-06 gates; `notify_lifecycle_submitted` |
| Send back to draft | `in_review -> draft` | `approve` | **yes** | |
| Approve and put in force | `in_review -> in_force` | **`approve`** | no | stamps approval (RG-DOC-07); supersedes the previous version (RG-DOC-01); recomputes the review date (RG-DOC-11); activates a `draft` document whose first version this is |
| Supersede | `in_force -> superseded` | `approve` | **yes** | only as the system side effect of RG-DOC-01 / RG-DOC-09, or explicitly to withdraw a version without a successor (the document then has no version in force and is flagged) |

The side effects need the bespoke transition endpoint `documents:policy-version-transition` (`lifecycle_transition_url_name`), which wraps `transition_to()` in one `transaction.atomic()` block.

### 3.3 `acknowledgement_campaign`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Draft | DRAFT | no | no | **yes** | neutral |
| `running` | Running | INTERMEDIATE | **yes** | no | no | info |
| `closed` | Closed | INTERMEDIATE | **yes** | no | no | success |
| `archived` | Archived | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Side effect |
| --- | --- | --- | --- | --- |
| Launch | `draft -> running` | `approve` | no | RG-DOC-14 gate; resolves the audience (RG-DOC-15); notifies every addressee |
| Close | `running -> closed` | `update` | no | pending rows become `expired`; rate frozen |
| Archive | `closed -> archived`, `draft -> archived` | `approve` | **yes** | |

---

## 4. Permissions and access control

`PERMISSION_REGISTRY` gains a `documents` module (`MODULE_LABELS["documents"] = _("Documents")`) with two features :

| Codename | Description |
| --- | --- |
| `documents.policy.read` | List and read documents, their versions and PDFs |
| `documents.policy.create` | Create a document and its first version |
| `documents.policy.update` | Edit a document's identity, create a new version, edit and submit a draft version |
| `documents.policy.approve` | Approve and put a version in force, send a version back, activate / retire a document, record a review without change |
| `documents.policy.delete` | Delete a draft document or a draft version |
| `documents.acknowledgement.read` | Read campaigns, their audience and completion |
| `documents.acknowledgement.create` | Create a campaign |
| `documents.acknowledgement.update` | Edit a draft campaign, close a running one, add newcomers, excuse a row |
| `documents.acknowledgement.approve` | Launch and archive a campaign |
| `documents.acknowledgement.delete` | Delete a draft campaign |

Acknowledging one's own row needs no permission (RG-DOC-17).

System groups follow the platform pattern : Super Administrateur and Administrateur get every codename; RSSI / DPO get read, create, update, approve; Contributeur gets read, create, update; Auditeur and Lecteur get read. A migration creates the rows and attaches them.

---

## 5. API

Base path `/api/v1/documents/`. The viewsets follow the house pattern (`ModulePermission`, `ScopeFilterAPIMixin`, `LifecycleAPIMixin`, `status` exposed read-only from `workflow_state`).

| Method | Path | Description |
| --- | --- | --- |
| `GET` / `POST` | `policies/` | List (filters `status`, `type`, `owner_id`, `scope_id`, `review_before`, `overdue`) / create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `policies/{id}/` | Read / update identity / delete a draft |
| `GET` / `POST` | `policies/{id}/transition/` | Allowed transitions / perform one |
| `POST` | `policies/{id}/record-review/` | Reviewed, no change (RG-DOC-13) |
| `POST` | `policies/{id}/new-version/` | Draft the next version from the one in force (RG-DOC-05) |
| `GET` | `policies/{id}/history/` | Timeline |
| `GET` / `POST` | `policy-versions/` | List (filter `policy_id`, `status`) / create a draft |
| `GET` / `PATCH` / `DELETE` | `policy-versions/{id}/` | Read / edit a draft (RG-DOC-02) / delete a draft |
| `GET` / `POST` | `policy-versions/{id}/transition/` | Through the bespoke transition service |
| `GET` / `POST` | `acknowledgement-campaigns/` | List / create |
| `GET` / `PATCH` / `DELETE` | `acknowledgement-campaigns/{id}/` | Read / edit a draft / delete a draft |
| `GET` / `POST` | `acknowledgement-campaigns/{id}/transition/` | Launch, close, archive |
| `POST` | `acknowledgement-campaigns/{id}/add-newcomers/` | Re-resolve the audience (RG-DOC-15) |
| `GET` | `acknowledgements/` | Rows the caller may read (campaign readers) plus the caller's own |
| `GET` | `acknowledgements/mine/` | The caller's own rows, pending first |
| `POST` | `acknowledgements/{id}/acknowledge/` | The addressee acknowledges (RG-DOC-16 / RG-DOC-17) |
| `POST` | `acknowledgements/{id}/excuse/` | Excuse a pending row with a reason (RG-DOC-19) |

The PDF is uploaded through the web form only (binary payloads are out of scope for the JSON API and MCP, as for contracts); the serializer exposes `document_url`, `has_pdf` and `pdf_sha256`.

---

## 6. MCP tools

`_register_documents_tools()` in `mcp/tools.py`, a `TOPIC_DOCUMENTS` help topic, and the `PLCY` / `PLVR` / `ACKC` reference prefixes in `HELP_TEXT`.

- `_register_crud` for `policy`, `policy_version` and `acknowledgement_campaign` (list, get, create, batch create, update, delete, transition, allowed transitions, history), with `m2m_fields` for scopes, linked requirements, audience users / groups / roles, and `_html_field()` for `content`.
- `new_policy_version(policy_id, bump="minor"|"major")`, `record_policy_review(policy_id, comment)`.
- `get_policy_in_force(policy_id)` : the current version with its content, approval and effective date.
- `list_my_pending_acknowledgements()` and `acknowledge_policy_version(acknowledgement_id)` : the MCP client acts as the authenticated user, so RG-DOC-17 holds.
- `get_campaign_progress(campaign_id)` : counts by status and the completion rate.

`assistant/catalog.py` gains read-only `ToolSpec` entries for listing documents, reading the version in force and reading campaign progress.

---

## 7. Notifications

New `NotificationType` values with `notify_*` helpers in `accounts/notifications.py` (rendered per recipient language, created in the transaction, delivered `on_commit`); an accounts migration alters the choices.

| Event | Recipients | Channel |
| --- | --- | --- |
| `POLICY_REVIEW_DUE` : daily sweep, `next_review_date` within 30 days | The document owner | In-app, email |
| `POLICY_REVIEW_OVERDUE` : same sweep, review date passed | The owner, holders of `documents.policy.approve` in scope | In-app, email |
| `POLICY_VERSION_IN_FORCE` : a version is put in force | The owner, and the members of the audience of the previous version's campaigns | In-app |
| `ACKNOWLEDGEMENT_REQUESTED` : campaign launch, or a newcomer added | The addressee | In-app, email |
| `ACKNOWLEDGEMENT_REMINDER` : daily sweep, 7 days before `due_date` and on the day after it | Addressees with a pending row | In-app, email |

Submission for review uses the existing `LIFECYCLE_SUBMITTED` notification (RG-LC-06), with no module-specific code.

---

## 8. User interface

All pages follow the [UI components](../../sdk/ui-components.md) anatomies.

- **Sidebar** : a new **Documents** section between Compliance and Incidents, with *Policies* and *Acknowledgement campaigns*. Everyone sees *To acknowledge* (their own pending rows) in the user menu, with a count badge.
- **Policy list** (`/documents/policies/`) : columns reference, title, type, owner, version in force, effective from, next review (red when overdue), acknowledgement rate of the latest campaign, state. Rail : active documents, overdue reviews, documents without a version in force, average acknowledgement rate. Filters on type, owner, scope, state, overdue.
- **Policy detail** : stepper (`policy`), rail (lifecycle stage, version in force, next review, acknowledgement rate). Cards : *Version in force* (rendered rich text, PDF download with its SHA-256, approval line "Approved by X on D, effective from D"), *Versions* (flush table of every version with label, state, approval, change summary; "New version" action), *Structure* (parent and children), *Requirements*, *Campaigns*, *Review* ("Reviewed, no change" action, last review), traceability card.
- **Version detail** : stepper (`policy_version`, through the bespoke endpoint), the content, the PDF, the change summary, the approval, a banner on a superseded version ("Superseded by PLVR-n on D") linking to the version in force.
- **Campaign detail** : stepper, rail (audience, acknowledged, pending, rate), the audience table (person, status, acknowledged at, excuse reason) with filters, "Add newcomers" and "Excuse" actions.
- **To acknowledge** (`/documents/acknowledge/`) : the user's pending rows; opening one shows the version content and the statement *"I have read and understood {title} version {label}"* with a single **Acknowledge** button. The same page lists the user's past acknowledgements.
- Forms are the drawer modals, with their one-line page fallbacks; delete confirmations use the shared shells.

Platform surfaces : global search (documents and versions), calendar (`documents` category : next review dates, campaign due dates), dashboard widget *Documents* (overdue reviews, documents without a version in force, running campaigns and their rates), kanban (the current user's pending acknowledgements in *To do*), predefined indicators `policies_overdue_review` and `acknowledgement_rate`, help banners on the four pages.

---

## 9. Technical considerations

### 9.1 App wiring checklist

- [ ] `INSTALLED_APPS` gains `"documents"`; `DocumentsConfig.ready()` imports `documents.lifecycles` and the signal handlers.
- [ ] Models, admin (`SimpleHistoryAdmin`), initial migration; `HistoricalRecords(excluded_fields=["file_content"])` on `PolicyVersion`.
- [ ] `PERMISSION_REGISTRY`, `MODULE_LABELS`, the permission migration attaching the rows to the six system groups.
- [ ] `core/navigation.py` `NAV_TREE` entries; `MODULE_ACCENTS["documents"]` with `--module-accent-documents` / `-soft` in both token blocks of `static/css/cairn/00-tokens.css`; the sidebar section.
- [ ] Calendar categories, dashboard widget (and its context variables), kanban builder, global search categories, predefined indicators.
- [ ] `IsmsChange.affected_documents` (M2M, with a migration) and the management review card; `TrustCenterDocument.policy` (FK `PROTECT`, with a migration) and the one-of invariant extended to three sources.
- [ ] REST routes under `/api/v1/documents/`, MCP tools, assistant catalog entries.
- [ ] The daily sweep (review reminders, acknowledgement reminders) as a management command scheduled like the existing deadline sweeps.
- [ ] `scripts/seed_demo_data.py` : a Voltara document set (information security policy with three versions, access control policy, acceptable use charter, backup procedure under the operations policy, an incident response procedure), each put in force through `transition_to(..., enforce_permission=False)`; one running campaign with mixed acknowledgements, one closed.
- [ ] Translations (with `msgctxt "document"` where a label collides, e.g. "Active", "Retired"), help banners, user guide page, README feature table, CHANGELOG.

### 9.2 History and audit trail

Every model is history-tracked. A version's content is frozen from `in_review` (RG-DOC-02), so the history of a version after submission only records transitions and approval stamps : the approved text and its SHA-256 are the record. Acknowledgement rows are append-only (RG-DOC-16).

### 9.3 Security

- The PDF download view checks `documents.policy.read` and the document's scopes; the version's SHA-256 is shown so a copy can be verified.
- Rich text is sanitized on save and on render (`clean_html`, the Trust Center sanitizer).
- The Trust Center serves a policy only through the existing public document view and its dual gate; the public serializer exposes no internal field of the policy (owner, requirements, history).

---

## 10. Acceptance criteria

- [ ] Putting a version in force supersedes the previous one in the same transaction, with a recorded lifecycle event; at no time can two versions of a document be in force.
- [ ] A submitted version's content cannot be changed through the form, the API or MCP.
- [ ] The next review date follows the version in force and the review frequency; "Reviewed, no change" recomputes it and is recorded.
- [ ] A launched campaign creates exactly one row per resolved addressee; only the addressee can acknowledge it; the row is immutable; superseding the version closes the campaign and expires its pending rows.
- [ ] The Trust Center entry of a policy serves the current version and disappears when the document has none.
- [ ] Scope tenancy holds on every list, detail, API and MCP surface, including versions and acknowledgement rows; a user always sees their own pending rows.
- [ ] Every page renders in light and dark, at desktop and mobile widths, with the lifecycle stepper as the only way to change a state.
- [ ] Every string is translated; the generated reference (`generate_docs`) and the wiki check are clean.

---

## 11. Out of scope for v0.37.0

- A side-by-side diff between two versions (the history already shows field changes; a rendered diff of the rich text is a later addition).
- A register of policy exceptions and waivers (deviation, justification, expiry, risk acceptance link).
- Electronic signature of a version (approval remains the recorded lifecycle transition).
- A future-dated `effective_from` (approved now, in force later), which needs an intermediate `approved` step and a daily activation job.
- Quizzes or attestation questions in a campaign (beyond the single acknowledgement statement).

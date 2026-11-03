# Policy

`documents.models.policy.Policy`

A governing document of the ISMS : the information security policy (ISO/IEC 27001:2022 clause 5.2), a topic-specific policy (A.5.1), or a procedure, standard, charter or guideline that implements one. The `Policy` row is the document's **identity** : what it is, who owns it, what it covers, when it is reviewed. Its **content** lives in its [versions](policy-version.md), of which at most one is in force (RG-DOC-01).

File: `documents/models/policy.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`PLCY`**, e.g. `PLCY-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail. `LIFECYCLE_NAME = "policy"` (see [README §3.1](README.md#31-policy-the-document)); its exit step `archived` is labelled *Retired*. `workflow_perm_namespace = "documents.policy"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `PLCY-N`, unique | Business reference |
| `title` | string | required, max 255 | Document title, e.g. `Access control policy` |
| `document_type` | enum | required, default `policy` | See `DocumentType` below |
| `summary` | text | optional | One-paragraph purpose, shown in lists and on the Trust Center |
| `classification` | enum | required, default `internal` | `assets.constants.DataClassification` (`public`, `internal`, `confidential`, `restricted`, `secret`). A Trust Center publication requires `public` (RG-DOC-21 is complemented by this check in the Trust Center form). |
| `parent` | relation | FK -> self, `PROTECT`, optional | The document this one implements (a procedure under a policy). Reverse accessor `children`. No cycle (RG-DOC-10). |
| `owner` | relation | FK -> User, `SET_NULL`, optional | Accountable owner : maintains the document, receives review reminders |
| `approver` | relation | FK -> User, `SET_NULL`, optional | Expected approver of new versions (informative : the approval itself is whoever performs the `approve` transition, RG-DOC-07) |
| `review_frequency_months` | int | required, default `12`, 1 to 60 | Review cycle |
| `next_review_override` | date | optional | Explicit next review date, overriding the derived one |
| `next_review_date` | date | optional, indexed, not editable | Derived (RG-DOC-11), stored for the calendar, the dashboard and filters |
| `last_reviewed_at` | datetime | optional, not editable | Stamped by "Reviewed, no change" (RG-DOC-13) or by a version put in force |
| `last_reviewed_by` | relation | FK -> User, `SET_NULL`, optional, not editable | |
| `workflow_state` | string | indexed, default `draft` | `policy` lifecycle step |
| `tags`, `version`, `created_by`, `created_at`, `updated_at` | | | From `BaseModel` |

### Relations

| Name | Type | Target | Reverse accessor | Description |
| --- | --- | --- | --- | --- |
| `scopes` | M2M | `context.Scope` | `policies` | ISMS scopes the document governs |
| `linked_requirements` | M2M | `compliance.Requirement` | `linked_policies` | The requirements the document answers (A.5.1, clause 5.2, A.5.15...). The requirement detail page lists them. |
| `applies_to_roles` | M2M | `context.Role` | `applicable_policies` | Roles the document is primarily addressed to (informative; also the default audience of a new campaign) |

Reverse accessors : `versions` ([PolicyVersion](policy-version.md), `CASCADE` only while draft, see deletion), `children`, `isms_changes` (`reports.IsmsChange.affected_documents`), `trust_center_documents` (`trust_center.TrustCenterDocument.policy`, `PROTECT`).

### Meta

- `ordering = ["reference"]`

## Enumerations

### `DocumentType`

| Value | Label | Typical use |
| --- | --- | --- |
| `policy` | Policy | The information security policy, a topic-specific policy |
| `procedure` | Procedure | How a policy is carried out, step by step |
| `standard` | Standard | Mandatory technical or organisational requirements (e.g. password standard) |
| `guideline` | Guideline | Recommended practice, not mandatory |
| `charter` | Charter | An acceptable use or user charter, typically acknowledged by every employee |
| `plan` | Plan | A plan of record (continuity plan, communication plan) |

## Computed properties and methods

- `version_in_force` : the version in the `in_force` step, or `None`.
- `latest_version` : the most recent version by `created_at`, whatever its step.
- `is_review_overdue` : `active` and `next_review_date < today` (RG-DOC-12).
- `compute_next_review_date()` : RG-DOC-11; called from `save()` and from the version transition service.
- `record_review(user, comment)` : RG-DOC-13.
- `new_version(user, bump="minor")` : RG-DOC-05; returns the new draft [PolicyVersion](policy-version.md).
- `ancestors()` : the parent chain, used by the cycle check and the breadcrumb.

## Validation

- `clean()` refuses a `parent` that is the document itself or one of its descendants (RG-DOC-10).
- `review_frequency_months` between 1 and 60.

## Deletion

A document is deletable only in `draft` (the `policy` lifecycle's only deletable step), which in practice means it has no version beyond draft. Its draft versions are deleted with it. A document with an in-force or superseded version is retired, never deleted; `TrustCenterDocument.policy` (`PROTECT`) and `IsmsChange.affected_documents` keep it referenced.

## References

- ISO/IEC 27001:2022 clause 5.2 (policy), clause 7.5 (documented information), A.5.1 (policies for information security)
- [PolicyVersion](policy-version.md), [AcknowledgementCampaign](acknowledgement-campaign.md)
- [README.md](README.md) : the RG-DOC rules, lifecycles, permissions, API, MCP, notifications, UI
- [Requirement](../m3-compliance/requirement.md), [Role](../m1-context/role.md), [IsmsChange](../management-review/isms-change.md), [Trust Center document](../m5-trust-center/document.md)

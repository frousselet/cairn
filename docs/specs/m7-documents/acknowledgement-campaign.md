# AcknowledgementCampaign

`documents.models.campaign.AcknowledgementCampaign`

A request, addressed to a defined audience, to confirm having read **one version** of a [Policy](policy.md). It is the A.5.1 evidence that a policy was "communicated to and acknowledged by relevant personnel" and the clause 7.3 evidence of awareness : who was asked, when, who confirmed, who did not.

File: `documents/models/campaign.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`ACKC`**, e.g. `ACKC-1`), `scopes` M2M (defaulting to the document's scopes), `tags`, `version`, `created_by`, `django-simple-history` audit trail. `LIFECYCLE_NAME = "acknowledgement_campaign"` (see [README §3.3](README.md#33-acknowledgement_campaign)). `workflow_perm_namespace = "documents.acknowledgement"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `ACKC-N`, unique | Business reference |
| `name` | string | required, max 255 | e.g. `Acceptable use charter 2.0 : all staff` |
| `policy_version` | relation | FK -> [PolicyVersion](policy-version.md), `PROTECT` | The version to acknowledge. Must be `in_force` at launch (RG-DOC-14). Reverse accessor `campaigns`. |
| `message` | text | optional | Shown to each addressee above the content |
| `statement` | string | required, max 500, default *"I have read and understood {title} version {label}, and I will comply with it."* | The sentence the addressee confirms; snapshotted on each row at acknowledgement (RG-DOC-16) |
| `due_date` | date | required | Acknowledgement deadline; drives reminders and the calendar |
| `launched_at` | datetime | optional, not editable | Stamped at launch |
| `closed_at` | datetime | optional, not editable | Stamped at closure (manual or RG-DOC-18) |
| `workflow_state` | string | indexed, default `draft` | `acknowledgement_campaign` lifecycle step |
| `tags`, `version`, `created_by`, `created_at`, `updated_at` | | | From `BaseModel` |

### Audience

| Name | Type | Target | Description |
| --- | --- | --- | --- |
| `audience_users` | M2M | User | Named addressees |
| `audience_groups` | M2M | `accounts.Group` | Every active member at launch |
| `audience_roles` | M2M | `context.Role` | Every active `Role.assigned_users` member at launch |

The audience is resolved **once, at launch** (RG-DOC-15) into [PolicyAcknowledgement](policy-acknowledgement.md) rows; editing the audience is only possible in `draft`. "Add newcomers" (running campaigns) re-resolves it and creates the missing rows only.

## Computed properties

- `counts` : rows by status (`pending`, `acknowledged`, `excused`, `expired`).
- `completion_rate` : RG-DOC-19, as an integer percentage, frozen at closure.
- `is_overdue` : `running` and `due_date < today`.

## Validation

- Launch is refused when the target version is not `in_force` (RG-DOC-14) or when the resolved audience is empty.
- `due_date` cannot precede the launch date.

## Deletion

Only a `draft` campaign (which has no rows) is deletable. A launched campaign is closed, then archived; its rows are kept.

## References

- ISO/IEC 27001:2022 A.5.1, clause 7.3 (awareness), A.6.3 (information security awareness, education and training)
- [PolicyAcknowledgement](policy-acknowledgement.md), [PolicyVersion](policy-version.md), [README.md](README.md)

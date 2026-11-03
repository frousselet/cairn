# PolicyAcknowledgement

`documents.models.acknowledgement.PolicyAcknowledgement`

One addressee of one [campaign](acknowledgement-campaign.md) : the request to a person to acknowledge a [policy version](policy-version.md), and, once given, the record of that acknowledgement. It is a **write-once** evidence row (RG-DOC-16), in the same family as `incidents.EvidenceCustodyEvent` : not a governed domain element, so it runs no lifecycle and carries no reference.

File: `documents/models/acknowledgement.py`

Plain `models.Model` with a UUID PK and `django-simple-history`. Scopes are inherited through `campaign__policy_version__policy__scopes` (RG-DOC-22), and the addressee always sees their own rows.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `campaign` | relation | FK -> [AcknowledgementCampaign](acknowledgement-campaign.md), `PROTECT` | Reverse accessor `acknowledgements` |
| `user` | relation | FK -> User, `PROTECT` | The addressee |
| `status` | enum | required, default `pending` | `pending`, `acknowledged`, `excused`, `expired` |
| `requested_at` | datetime | auto | When the row was created (launch or "Add newcomers") |
| `acknowledged_at` | datetime | optional, not editable | Stamped by the addressee's own action |
| `statement` | string | optional, max 500, not editable | The campaign statement as it read when acknowledged, with the title and version label filled in |
| `channel` | enum | optional, not editable | `web`, `api`, `mcp` : the surface the acknowledgement came through |
| `excused_at` | datetime | optional, not editable | |
| `excused_by` | relation | FK -> User, `SET_NULL`, optional, not editable | |
| `excuse_reason` | text | required when excused | RG-DOC-19 |
| `last_reminded_at` | datetime | optional, not editable | Set by the reminder sweep |

### Meta

- `UniqueConstraint(fields=["campaign", "user"])` : one row per person and campaign.
- `ordering = ["campaign", "user__last_name", "user__first_name"]`

## Status transitions

Status is a plain column, deliberately not a lifecycle : a row moves along one of three one-way paths, each stamped, none reversible.

| From | To | Who | Stamps |
| --- | --- | --- | --- |
| `pending` | `acknowledged` | the addressee only (RG-DOC-17) | `acknowledged_at`, `statement`, `channel` |
| `pending` | `excused` | holder of `documents.acknowledgement.update` | `excused_at`, `excused_by`, `excuse_reason` |
| `pending` | `expired` | the system, at campaign closure (manual or RG-DOC-18) | |

`acknowledge(user, channel)` and `excuse(user, reason)` are the only write paths; `save()` refuses any change to a row that is no longer `pending`, and deletion is refused while the campaign exists (`PROTECT`).

## References

- [AcknowledgementCampaign](acknowledgement-campaign.md), [README.md](README.md) : RG-DOC-15 to RG-DOC-19

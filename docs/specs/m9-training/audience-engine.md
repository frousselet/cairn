# Audience engine

`core.audience.AudienceCampaign` and `core.audience.AudienceRow`

The shared mechanics of a campaign that asks a defined audience to do something and keeps one write-once evidence row per person. Extracted from the documents acknowledgement campaigns (RG-DOC-15 to RG-DOC-19) so module 9 reuses them unchanged. Two abstract Django models; no table of their own.

## `AudienceCampaign` (abstract)

| Field | Type | Description |
| --- | --- | --- |
| `due_date` | date | Required |
| `launched_at`, `closed_at` | datetime, not editable | Stamped by the lifecycle side effects |
| `audience_users` | M2M User, `related_name="%(app_label)s_%(class)s_audience"` | Named addressees |
| `audience_groups` | M2M `accounts.Group`, same pattern | Members at launch |
| `audience_roles` | M2M `context.Role`, same pattern | Assigned users at launch |

Class attributes set by the concrete model : `row_model` (the `AudienceRow` subclass), `rows_accessor` (its reverse name, `acknowledgements` / `enrolments`), `done_status` (counted as done in the rate), `excused_status`.

Methods :

- `resolve_audience()` : active users named, members of the groups, assignees of the roles, de-duplicated.
- `create_rows(users)` : one row per user not already present, with `bulk_create_with_history`.
- `add_newcomers(user)` : running campaigns only; creates the missing rows, records a change reason, calls the concrete `notify_requested(rows)`.
- `launch_rows()` / `expire_pending_rows()` : called by the concrete `transition_to()` on launch / close.
- `counts`, `completion_rate` (done / (all - excused)), `is_overdue`.

## `AudienceRow` (abstract)

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | PK |
| `user` | FK User, `PROTECT` | Addressee |
| `status` | string, indexed | Choices set by the concrete model; `pending` is the shared initial value |
| `requested_at` | datetime, auto | |
| `last_reminded_at` | datetime, not editable | Set by the sweeps |
| `excused_at`, `excused_by`, `excuse_reason` | | The shared `excuse(user, reason)` path |

`save()` refuses any change once `status != pending`; `delete()` is refused; `expire()` moves a pending row to `expired`.

## Adoption by module 7

`AcknowledgementCampaign` and `PolicyAcknowledgement` inherit the engine. Field names, statuses and behaviour are unchanged; the only schema change is the related name of the three audience M2Ms (`acknowledgement_campaigns` becomes `documents_acknowledgementcampaign_audience`), which no code reads. The module 7 tests pass unchanged.

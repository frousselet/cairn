# TrainingEnrolment

`training.models.enrolment.TrainingEnrolment`

One addressee of one [campaign](training-campaign.md) : the request to complete the course and, once given, the record of the completion. A write-once evidence row on the shared [audience engine](audience-engine.md) (`core.audience.AudienceRow`), like `documents.PolicyAcknowledgement`.

File: `training/models/enrolment.py`

Plain model with UUID PK and history; scopes through `campaign__scopes`; the addressee always sees their own rows.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `campaign` | relation | FK -> campaign, `PROTECT` | Reverse `enrolments` |
| `user` | relation | FK -> User, `PROTECT` | From the engine |
| `status` | enum | default `pending` | `pending`, `completed`, `failed`, `excused`, `expired` |
| `requested_at`, `last_reminded_at` | datetime | | From the engine |
| `completed_on` | date | not editable | RG-TRN-10 |
| `score` | integer | optional, 0 to 100, not editable | RG-TRN-09 |
| `channel` | enum | not editable | `trainer`, `self`, `import`, `api`, `mcp` |
| `recorded_by` | relation | FK -> User, `SET_NULL`, not editable | Who recorded it (the addressee when self-attested) |
| `statement` | string | max 500, not editable | The attestation confirmed on self-attestation |
| `import_file_name`, `import_sha256` | string | not editable | RG-TRN-13 |
| `excused_at`, `excused_by`, `excuse_reason` | | | RG-TRN-07 |

`UniqueConstraint(campaign, user)`.

## Write paths

`complete(user, completed_on, score=None, channel)`, `self_attest(user)`, `excuse(user, reason)`, `expire()`; `save()` refuses any change once the row has left `pending`, `delete()` is refused.

## References

- [README.md](README.md) : RG-TRN-07 to RG-TRN-13

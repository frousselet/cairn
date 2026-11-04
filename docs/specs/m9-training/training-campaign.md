# TrainingCampaign

`training.models.campaign.TrainingCampaign`

One [course](training-course.md) delivered to a defined audience by a due date, optionally as a scheduled session. Built on the shared [audience engine](audience-engine.md) : the audience is resolved once at launch into write-once [enrolments](training-enrolment.md) (RG-TRN-05).

File: `training/models/campaign.py`

`ScopedModel` + `core.audience.AudienceCampaign` : `reference` (prefix **`TRCA`**), `scopes` (default : the course's), `tags`, history. `LIFECYCLE_NAME = "training_campaign"`. `workflow_perm_namespace = "training.campaign"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `name` | string | required, max 255 | e.g. `Awareness 2026 : all staff` |
| `course` | relation | FK -> [TrainingCourse](training-course.md), `PROTECT` | Must be `active` at launch |
| `message` | text | optional | Shown to each addressee |
| `session_date`, `session_end` | datetime | optional | A scheduled session (classroom, webinar) |
| `location` | string | optional, max 500 | Room or meeting link |
| `trainer` | relation | FK -> User, `SET_NULL`, optional | |
| `due_date`, `launched_at`, `closed_at` | | | From the audience engine |
| `audience_users`, `audience_groups`, `audience_roles` | M2M | | From the audience engine |

## Computed

`counts`, `completion_rate` (RG-TRN-11), `is_overdue`, from the engine.

## References

- [README.md](README.md) : RG-TRN-05, RG-TRN-06, RG-TRN-11 to RG-TRN-13

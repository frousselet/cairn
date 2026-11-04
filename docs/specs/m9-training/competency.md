# Competency

`training.models.competency.Competency`

A competence the organisation requires (clause 7.2 a) : *"Annual security awareness"* for everyone, *"Secure development"* for developers, *"Incident handling"* for the on-call rota. It is **required** for the members of its roles and groups and **satisfied** by a valid completion of any of its courses (RG-TRN-03). The [matrix](README.md#24-competency-matrix) is derived from it.

File: `training/models/competency.py`

`ScopedModel` subclass : `reference` (prefix **`CMPT`**), `scopes`, `tags`, history. `LIFECYCLE_NAME = "competency"`. `workflow_perm_namespace = "training.competency"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `name` | string | required, max 255 | |
| `description` | text | optional | What a competent person can do |
| `required_for_roles` | M2M | `context.Role`, reverse `required_competencies` | Assigned users of these roles need it |
| `required_for_groups` | M2M | `accounts.Group`, reverse `required_competencies` | Members of these groups need it |
| `satisfied_by` | M2M | [TrainingCourse](training-course.md), reverse `competencies` | Any of these courses satisfies it; required to activate |
| `owner` | relation | FK -> User, `SET_NULL`, optional | Receives the expiring notifications in copy |
| `workflow_state` | string | default `draft` | `competency` lifecycle |

## Computed

- `required_users()` : RG-TRN-03 (active users, de-duplicated).
- `status_for(user)` : RG-TRN-14, with the satisfying completion and its `valid_until`.
- `coverage()` : RG-TRN-15.

## References

- ISO/IEC 27001:2022 clause 7.2
- [README.md](README.md) : RG-TRN-03, RG-TRN-14 to RG-TRN-16

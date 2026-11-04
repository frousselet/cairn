# ContinuityExercise

`continuity.models.exercise.ContinuityExercise`

A test of a [plan](continuity-plan.md) (ISO 22301 clause 8.5; ISO/IEC 27001:2022 A.5.30) : the scenario, who took part, how long recovery took against the objective, the outcome and the lessons learned (RG-BCM-12 to RG-BCM-15).

File: `continuity/models/exercise.py`

`BaseModel` : `reference` (prefix **`BCEX`**), history; scopes through `plan__scopes`. `LIFECYCLE_NAME = "continuity_exercise"`. `workflow_perm_namespace = "continuity.exercise"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `plan` | relation | FK -> plan, `PROTECT` | Must be `active` when created |
| `name` | string | required, max 255 | |
| `exercise_type` | enum | required | `tabletop`, `walkthrough`, `simulation`, `technical_recovery`, `full_interruption` |
| `scheduled_on` | date | required | |
| `facilitator` | relation | FK -> User, `SET_NULL`, optional | |
| `participants` | M2M | User | |
| `scenario`, `objectives` | text | optional | |
| `conducted_on` | date | required to record results, not in the future | |
| `achieved_recovery_minutes` | integer | optional | |
| `outcome` | enum | required to record results | `success`, `partial`, `fail` |
| `lessons_learned` | text | required when `partial` or `fail` | |
| `validated_by`, `validated_at` | | not editable | |

Results are frozen from `conducted` (RG-BCM-12). Reverse `findings` from `Finding.continuity_exercise`.

## Computed

`objective_met` (RG-BCM-14), `needs_finding`.

## References

- [README.md](README.md) : RG-BCM-12 to RG-BCM-15

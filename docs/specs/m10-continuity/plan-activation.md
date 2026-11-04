# PlanActivation

`continuity.models.activation.PlanActivation`

A real use of a [plan](continuity-plan.md), declared from the plan or from an incident, with its write-once log (RG-BCM-16 to RG-BCM-19).

File: `continuity/models/activation.py`

`BaseModel` : `reference` (prefix **`BCAC`**), history; scopes through `plan__scopes`. `LIFECYCLE_NAME = "plan_activation"` (initial step `active`). `workflow_perm_namespace = "continuity.activation"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `plan` | relation | FK -> plan, `PROTECT` | `UniqueConstraint(plan)` where `workflow_state = active` |
| `incident` | relation | FK -> `incidents.Incident`, `SET_NULL`, optional | Reverse `plan_activations` |
| `reason` | text | required | |
| `activated_at`, `activated_by` | | not editable | |
| `stood_down_at`, `stood_down_by` | | not editable | RG-BCM-18 |
| `achieved_recovery_minutes` | integer | not editable | RG-BCM-18 |

## ActivationLogEntry

`continuity.models.activation.ActivationLogEntry` : a write-once row (RG-BCM-17).

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | PK |
| `activation` | FK -> activation, `PROTECT` | Reverse `log_entries` |
| `logged_at` | datetime, auto | Never typed |
| `author` | FK -> User, `SET_NULL` | |
| `text` | text | required |
| `step` | FK -> [RecoveryStep](recovery-step.md), `SET_NULL`, optional | The step reached, when the entry records one |
| `kind` | enum | `activated`, `note`, `step_reached`, `stood_down` |

`save()` refuses any change to an existing row; `delete()` is refused.

## References

- [README.md](README.md) : RG-BCM-16 to RG-BCM-19

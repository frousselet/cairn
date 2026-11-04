# RecoveryStep

`continuity.models.plan.RecoveryStep`

One ordered step of a [plan](continuity-plan.md) : what to do, who owns it, by when after activation. Child row, history-tracked, editable only while the plan is `draft` (RG-BCM-08).

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `plan` | relation | FK -> plan, `CASCADE` while draft | Reverse `steps` |
| `order` | integer | | Position |
| `title` | string | required, max 255 | |
| `description` | text | optional | |
| `owner_role` | relation | FK -> `context.Role`, `PROTECT` | Notified on activation (RG-BCM-19) |
| `target_minutes` | integer | >= 0 | Target time from activation; non-decreasing with `order` |

## References

- [README.md](README.md) : RG-BCM-07, RG-BCM-08, RG-BCM-10

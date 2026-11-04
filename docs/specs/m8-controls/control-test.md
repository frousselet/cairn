# ControlTest

`controls.models.control_test.ControlTest`

How a [control](control.md) is tested : the method, the procedure, what a pass looks like, and how often. A control has one or more tests (e.g. "design review" once a year, "operating effectiveness on a sample" every quarter). Each execution is a [run](control-test-run.md).

File: `controls/models/control_test.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`CTST`**), `tags`, `version`, `created_by`, history. Scopes are inherited through `scope_parent_lookup = "control__scopes"` (RG-CTL-19). `LIFECYCLE_NAME = "control_test"` (see [README §3.2](README.md#32-control_test)). `workflow_perm_namespace = "controls.test"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CTST-N`, unique | Business reference |
| `control` | relation | FK -> [Control](control.md), `PROTECT` | Reverse accessor `tests` |
| `name` | string | required, max 255 | e.g. `Quarterly sample of remote logins` |
| `objective` | text | optional | What the test establishes (design, operating effectiveness) |
| `method` | enum | required, default `inspection` | `inquiry`, `observation`, `inspection`, `reperformance`, `automated` |
| `procedure` | text | required to activate | The steps the tester follows |
| `acceptance_criteria` | text | required to activate | What a pass looks like (RG-CTL-06) |
| `frequency_months` | integer | required, 1 to 36, default 12 | Interval between two runs |
| `tester` | relation | FK -> User, `SET_NULL`, optional | Default performer of runs, recipient of due reminders |
| `first_due_date` | date | optional | Due date of the first run |
| `next_due_date` | date | indexed, optional, not editable | Derived (RG-CTL-07) |
| `activated_on` | date | optional, not editable | Stamped at activation |
| `last_reminded_at` | datetime | optional, not editable | Set by the sweep |
| `workflow_state` | string | indexed, default `draft` | `control_test` lifecycle step |

## Computed properties

- `latest_validated_run` : the validated run with the latest `performed_on` (ties : latest `reviewed_at`).
- `latest_result` : its result, or none.
- `is_overdue` : RG-CTL-07.
- `recompute_next_due_date()` : RG-CTL-07, idempotent.

## Validation

- Activation is refused unless the control is `planned` or `implemented` and `procedure` and `acceptance_criteria` are set (RG-CTL-06).
- The control cannot change once the test has runs.

## Deletion

Only a `draft` test without runs is deletable; otherwise it is retired (RG-CTL-08).

## References

- ISO/IEC 27001:2022 clause 9.1 (monitoring, measurement, analysis and evaluation)
- [ControlTestRun](control-test-run.md), [README.md](README.md) : RG-CTL-06 to RG-CTL-08

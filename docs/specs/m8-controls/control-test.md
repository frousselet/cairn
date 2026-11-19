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
| `method` | enum | required, default `inspection` (asked by the creation dialog with no answer preselected) | `inquiry`, `observation`, `inspection`, `reperformance`, `automated` |
| `procedure` | text | optional at creation, required to activate | The steps the tester follows |
| `acceptance_criteria` | text | optional at creation, required to activate | What a pass looks like (RG-CTL-06) |
| `frequency_months` | integer | required, 1 to 36, default 12 | Interval between two runs |
| `tester` | relation | FK -> User, `SET_NULL`, optional | Default performer of runs, recipient of due reminders. The creation dialog proposes the owner of the control, else whoever creates the test |
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

## Creation and completeness

A test is created short and completed on its page ([usability standard](../../sdk/usability-standard.md)).

- **Creation**, from the page of the control, asks on one screen : the name, the method (a decision : the select opens on *Choose...* and an answer is required), the frequency (12 months proposed) and the tester. The test opens on its page.
- **The edit form has three sections**, one per card of the page : `identity` (name, method, objective), `procedure` (procedure, acceptance criteria) and `planning` (frequency, tester, first due date, tags).
- **Completeness** (`ControlTest.COMPLETENESS`), listed on the page under *To complete* and returned as `completeness` by `GET /api/v1/controls/tests/{id}/` and `get_control_test` :

| Requirement | Key | Blocking |
| --- | --- | --- |
| The procedure is filled in | `procedure` | yes : before `active`, on every surface (RG-CTL-06) |
| The acceptance criteria are filled in | `acceptance_criteria` | yes : before `active`, on every surface (RG-CTL-06) |
| The test has a tester | `tester` | no |

A retired test is a closed record : its page lists nothing to complete and offers no edit.

## Validation

- Activation is refused unless the control is `planned` or `implemented` (checked first, in `transition_to`) and `procedure` and `acceptance_criteria` are set (the completeness, RG-CTL-06).
- The control cannot change once the test has runs.

## Deletion

Only a `draft` test without runs is deletable; otherwise it is retired (RG-CTL-08).

## References

- ISO/IEC 27001:2022 clause 9.1 (monitoring, measurement, analysis and evaluation)
- [ControlTestRun](control-test-run.md), [README.md](README.md) : RG-CTL-06 to RG-CTL-08

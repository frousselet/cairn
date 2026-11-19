# ControlTestRun

`controls.models.control_test_run.ControlTestRun`

One execution of a [test](control-test.md) : who tested, when, over which period, on which sample, with what result and which [evidence](control-test-evidence.md). It is frozen once submitted (RG-CTL-09) and validated by someone other than its performer (RG-CTL-11). Validated runs drive the control's effectiveness (RG-CTL-14).

File: `controls/models/control_test_run.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`CTRN`**), `version`, `created_by`, history. Scopes are inherited through `scope_parent_lookup = "test__control__scopes"`. `LIFECYCLE_NAME = "control_test_run"` (see [README §3.3](README.md#33-control_test_run)). `workflow_perm_namespace = "controls.test"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CTRN-N`, unique | Business reference |
| `test` | relation | FK -> [ControlTest](control-test.md), `PROTECT` | Must be `active` when the run is created. Reverse accessor `runs` |
| `performed_by` | relation | FK -> User, `PROTECT` | Defaults to the test's tester, else the creator |
| `performed_on` | date | required, not in the future | Date of the test |
| `period_start`, `period_end` | date | optional | Period the test covers (RG-CTL-10) |
| `sample_description` | text | optional | Population and sample tested |
| `result` | enum | optional at creation, required to submit | `pass`, `partial`, `fail`; empty reads *Not recorded yet* |
| `observations` | text | required to submit when `partial` or `fail` | What was found; becomes the description of a raised finding |
| `reviewed_by` | relation | FK -> User, `SET_NULL`, optional, not editable | Stamped at validation (RG-CTL-11) |
| `reviewed_at` | datetime | optional, not editable | Stamped at validation |
| `workflow_state` | string | indexed, default `draft` | `control_test_run` lifecycle step |

`FROZEN_FIELDS` : `test`, `performed_by`, `performed_on`, `period_start`, `period_end`, `sample_description`, `result`, `observations`; editable only in `draft` on every surface.

The reverse accessor `findings` (from `compliance.Finding.control_test_run`) lists the finding raised from the run (RG-CTL-16).

## Creation and completeness

A run is recorded short and completed on its page ([usability standard](../../sdk/usability-standard.md)).

- **Creation**, from the page of an active test, asks on one screen : who performed the test (the test's tester proposed), when (today proposed), and, once known, the result and the observations. The run opens on its page.
- **The edit form has two sections**, one per card of the page : `execution` (performer, date, period, sample) and `result` (result, observations). The evidence has its own card.
- **Completeness** (`ControlTestRun.COMPLETENESS`), listed on the page under *To complete* while the run is in progress and returned as `completeness` by `GET /api/v1/controls/runs/{id}/` and `get_control_test_run` :

| Requirement | Key | Blocking |
| --- | --- | --- |
| The result is recorded | `result` | yes : before `in_review`, on every surface (RG-CTL-10) |
| A partial or failed result has observations | `observations` | yes : before `in_review` (asked of a partial or failed run only) |
| The run has evidence | `evidence` | no : the line leads to the *Evidence* card |

A submitted run is frozen (RG-CTL-09) : its page lists nothing to complete and offers no edit.

## Validation

- RG-CTL-10 on submission (the result and the observations through the completeness, the period in `transition_to`); RG-CTL-11 on validation (the reviewer is not the performer).
- A run cannot be created on a test that is not `active`.

## Deletion

Only a `draft` run is deletable, with its evidence. Afterwards it is withdrawn (`archived`) with a comment and stays readable.

## References

- ISO/IEC 27001:2022 clause 9.1, 9.2 (evidence of monitoring results), 10.2 (nonconformity)
- [ControlTestEvidence](control-test-evidence.md), [Finding](../m3-compliance/finding.md), [README.md](README.md) : RG-CTL-09 to RG-CTL-16

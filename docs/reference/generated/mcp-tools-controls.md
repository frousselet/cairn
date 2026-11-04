<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Controls

Input schemas for the 33 `controls` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `batch_create_control_test_runs`

Record several runs (in progress) in one call (max 500). Every test_id must be an active test within the caller's scopes, or nothing is created.

Requires `controls.test.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Run objects: test_id (required), performed_by_id, performed_on, period_start, period_end, sample_description, result, observations. |
| `match_on` | `array` | - | Optional business key (writable field names) used to find an existing run to update; a submitted run refuses any change. |

## `batch_create_control_tests`

Create or upsert several draft control tests in one call (max 500). Every control_id must be a control within the caller's scopes and not retired, or nothing is created.

Requires `controls.test.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Test objects: control_id, name (required), objective, method, procedure, acceptance_criteria, frequency_months, tester_id, first_due_date. |
| `match_on` | `array` | - | Optional business key (writable field names, e.g. ["control_id", "name"]) used to find an existing test to update. |

## `batch_create_controls`

Create or upsert several proposed controls in one call (max 500). Every link must be within the caller's scopes and linkable, or nothing is created. Pass 'match_on' (e.g. ["name"]) to update matching controls instead of duplicating them.

Requires `controls.control.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Control objects: name, description (required), theme, nature, automation, owner_id, implemented_on, scope_ids and the *_ids link arrays. |
| `match_on` | `array` | - | Optional business key (writable scalar field names) used to find an existing control to update. |

## `control_allowed_transitions`

List the lifecycle transitions the caller may perform on a control from its current state.

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `control_test_allowed_transitions`

List the lifecycle transitions the caller may perform on a control test from its current state.

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `control_test_run_allowed_transitions`

List the lifecycle transitions the caller may perform on a control test run from its current state.

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `create_control`

Create a proposed (draft) control: a durable practice the organisation operates, with its theme, nature, owner, scopes and links to requirements, risks, treatment plans, PACS measures, support assets, objectives and documents. Effectiveness is derived from validated test runs and cannot be set. Plan it or declare it implemented with transition_control. To bootstrap a register from a framework, prefer create_controls_from_requirements.

Requires `controls.control.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Control name, e.g. 'Multi-factor authentication on remote access'. |
| `description` | `string` | yes | How the control operates: what is done, by whom, on what (required). |
| `theme` | `string` | - | ISO/IEC 27002:2022 theme (default 'technological'). |
| `nature` | `string` | - | Control type attribute (default 'preventive'). |
| `automation` | `string` | - | How the control is operated (default 'manual'). |
| `owner_id` | `string` | - | UUID of the accountable owner (receives the failed-test notifications). Use list_users. |
| `implemented_on` | `string` | - | Date the control started operating (ISO 8601 date), never in the future. Stamped with today when declared implemented without one (RG-CTL-02). |
| `scope_ids` | `array` | - | Scopes of the control (within your own). Its tests and runs inherit them. |
| `requirement_ids` | `array` | - | Requirements the control satisfies, from any framework. Use list_requirements. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `risk_ids` | `array` | - | Risks the control treats. Use list_risks. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `treatment_plan_ids` | `array` | - | Risk treatment plans that create or reinforce the control. Use list_risk_treatment_plans. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `pacs_measure_ids` | `array` | - | EBIOS RM PACS measures that create or reinforce the control. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `support_asset_ids` | `array` | - | Support assets the control applies to. Use list_support_assets. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `objective_ids` | `array` | - | Objectives the control contributes to. Use list_objectives. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `policy_ids` | `array` | - | Documents (policies, procedures, standards) that describe the control. Use list_policys. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |

## `create_control_test`

Create a draft test of a control: method, procedure, acceptance criteria, frequency and default tester. Activate it with transition_control_test(target_state='active') once the control is planned or implemented and the procedure and acceptance criteria are written (RG-CTL-06); the next due date is then derived (RG-CTL-07).

Requires `controls.test.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `control_id` | `string` | yes | UUID of the control this test belongs to (not a retired one). Cannot change once the test has runs. Use list_controls. |
| `name` | `string` | yes | Test name, e.g. 'Quarterly sample of remote logins'. |
| `objective` | `string` | - | What the test establishes (design, operating effectiveness). |
| `method` | `string` | - | Test method (default 'inspection'). |
| `procedure` | `string` | - | The steps the tester follows. Required to activate the test (RG-CTL-06). |
| `acceptance_criteria` | `string` | - | What a pass looks like. Required to activate the test (RG-CTL-06). |
| `frequency_months` | `integer` | - | Interval between two runs in months, 1 to 36 (default 12). Drives the next due date. |
| `tester_id` | `string` | - | UUID of the default performer of the runs, who receives the due reminders. Use list_users. |
| `first_due_date` | `string` | - | Due date of the first run (ISO 8601 date). Defaults to the activation date. |

## `create_control_test_run`

Record a run (in progress) of an active control test. Fill the result and observations, attach evidence through the web form, then submit it with transition_control_test_run(target_state='in_review'): from then on its content is frozen (RG-CTL-09) and someone other than its performer validates it (RG-CTL-11).

Requires `controls.test.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `test_id` | `string` | yes | UUID of the active test this run executes (RG-CTL-09). Cannot change afterwards. Use list_control_tests. |
| `performed_by_id` | `string` | - | UUID of the person who performed the test. Defaults to the test's tester, else the caller. That person can never validate the run (RG-CTL-11). |
| `performed_on` | `string` | - | Date of the test (ISO 8601 date), never in the future. Defaults to today. |
| `period_start` | `string` | - | Start of the period the test covers (ISO 8601 date). |
| `period_end` | `string` | - | End of the period the test covers (ISO 8601 date), between period_start and performed_on (RG-CTL-10). |
| `sample_description` | `string` | - | Population and sample tested, e.g. '25 of 1,240 remote logins, March'. |
| `result` | `string` | - | Outcome against the acceptance criteria. Required to submit (RG-CTL-10). |
| `observations` | `string` | - | What was found. Required to submit a partial or failed result (RG-CTL-10); becomes the description of a raised finding. |

## `create_controls_from_requirements`

Bootstrap a control register from a framework (RG-CTL-05): for each selected applicable requirement that no control covers yet, create one proposed (draft) control named after the requirement, with its description as a starting point, the requirement linked and the framework's scopes. Requirements already covered (by a control in any step) or not applicable are skipped and reported; existing controls are never linked. Needs controls.control.create and compliance.framework.read on a framework within your scopes.

Requires `controls.control.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `framework_id` | `string` | yes | UUID of the framework, e.g. ISO/IEC 27001:2022 Annex A. Use list_frameworks. |
| `requirement_ids` | `array` | - | Only these requirements of the framework (default: all of them). Ids of other frameworks are ignored. |
| `scope_ids` | `array` | - | Scopes of the new controls (within your own). Default: the framework's scopes. |

## `delete_control`

Delete a proposed (draft) control that has no test. A control past draft, or with tests, is retired instead with transition_control(target_state='archived', comment=...).

Requires `controls.control.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_control_test`

Delete a draft control test that has no run. An active test is retired instead with transition_control_test(target_state='archived', comment=...).

Requires `controls.test.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_control_test_run`

Delete a run that is still in progress (draft), with its evidence. A submitted or validated run is withdrawn instead with transition_control_test_run(target_state='archived', comment=...) and stays readable.

Requires `controls.test.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_control`

Get a control by ID

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_control_effectiveness`

Explain a control's effectiveness (RG-CTL-14): the derived verdict (effective, partially_effective, not_effective, not_tested) and its date, and, for each active test, its latest validated run (result, date, reviewer) and next due date. 'is_effectiveness_stale' is true when the verdict rests on an overdue test (RG-CTL-15): the last verdict is kept, never silently downgraded.

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `control_id` | `string` | yes | UUID of the control. Use list_controls. |

## `get_control_history`

Return the change history of a control: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_control_test`

Get a control test by ID

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_control_test_history`

Return the change history of a control test: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control test |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_control_test_run`

Get one control test run by ID: result, period, sample, observations, performer, review stamps, the finding raised from it, and its evidence files (name, size, SHA-256 and the permission-checked download URL; the bytes themselves are not returned).

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_control_test_run_history`

Return the change history of a control test run: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control test run |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_requirement_coverage`

Read how a framework is covered by controls, the data behind the Statement of Applicability (RG-CTL-18): for each applicable, reportable requirement, its planned or implemented controls with their state and effectiveness, and an implementation summary (implemented, partial, planned, none). Proposed and retired controls never count; only the controls within your scopes are listed. 'totals' counts requirements per summary.

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `framework_id` | `string` | yes | UUID of the framework. Use list_frameworks. |

## `list_control_test_runs`

List control test runs with optional search and filters

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `test_id` | `string` | - | Filter by test_id |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `result` | `string` | - | Filter by result. |
| `performed_by_id` | `string` | - | Filter by performed_by_id |
| `reviewed_by_id` | `string` | - | Filter by reviewed_by_id |
| `control_id` | `string` | - | Restrict to the runs of the tests of one control. |

## `list_control_tests`

List control tests with optional search and filters

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `control_id` | `string` | - | Filter by control_id |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `tester_id` | `string` | - | Filter by tester_id |
| `method` | `string` | - | Filter by method |
| `overdue` | `boolean` | - | true: active tests whose next due date has passed (RG-CTL-07). |
| `due_before` | `string` | - | Tests due on or before this date (ISO 8601 date). |

## `list_controls`

List controls with optional search and filters

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `theme` | `string` | - | Filter by theme |
| `nature` | `string` | - | Filter by nature |
| `automation` | `string` | - | Filter by automation |
| `owner_id` | `string` | - | Filter by owner_id |
| `effectiveness` | `string` | - | Filter by derived effectiveness (RG-CTL-14). |
| `scope_id` | `string` | - | Restrict to the controls of one scope. |
| `requirement_id` | `string` | - | Restrict to the controls implementing one requirement. |
| `risk_id` | `string` | - | Restrict to the controls treating one risk. |
| `support_asset_id` | `string` | - | Restrict to the controls applying to one support asset. |
| `policy_id` | `string` | - | Restrict to the controls described by one document. |
| `objective_id` | `string` | - | Restrict to the controls contributing to one objective. |
| `framework_id` | `string` | - | Restrict to the controls implementing a requirement of one framework. |
| `test_overdue` | `boolean` | - | true: controls with at least one overdue active test (RG-CTL-15); false: none overdue. |

## `list_my_control_tests_due`

List the active control tests the authenticated user has to perform soon: those they are the tester of, or whose control they own when the test has no tester (the reminder recipients). Includes overdue tests; soonest due first. Record a run with create_control_test_run(test_id=...).

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `within_days` | `integer` | - | Horizon in days from today (default 14, the reminder window). |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_overdue_control_tests`

List the active control tests whose next due date has passed (RG-CTL-07), oldest due first, within your scopes: the control, the tester, the due date and the latest validated run. Overdue is derived, never a lifecycle step.

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `control_id` | `string` | - | Restrict to the tests of one control. |
| `tester_id` | `string` | - | Restrict to the tests of one tester. |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `raise_finding_from_run`

Raise a finding in the nonconformity register from a validated partial or failed test run (RG-CTL-16): source 'control_test', linked to the run, the run's observations as its description, the control's requirements as its related requirements, and the authenticated user as the person who raised it. Offered once per run: a second call is refused. The finding type is a judgement the caller makes.

Requires `controls.test.approve`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `run_id` | `string` | yes | UUID of the validated partial or failed run. Use list_control_test_runs(result='fail'). |
| `finding_type` | `string` | yes | major_nc (major nonconformity), minor_nc (minor nonconformity) or observation. |
| `recommendation` | `string` | - | Optional recommendation recorded on the finding. |

## `transition_control`

Change the lifecycle state of a control (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `controls.control.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_control_test`

Change the lifecycle state of a control test (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control test |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_control_test_run`

Move a test run through its lifecycle, as the authenticated user: 'in_review' (submit; needs a result, and observations for a partial or failed one, RG-CTL-10), 'draft' (send back, approve, comment required), 'validated' (approve; refused to the run's performer, superusers included, RG-CTL-11; recomputes the test's next due date and the control's effectiveness, RG-CTL-12), 'archived' (withdraw a validated run or cancel a draft, comment required).

Requires `controls.test.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the test run. |
| `target_state` | `string` | yes | Target step (see control_test_run_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory to send back, withdraw or cancel. |

## `update_control`

Update a control's identity and links (any step but retired). Each *_ids array replaces the current links; links already in place survive their target leaving a linkable step. Effectiveness, its date and the lifecycle step are not writable: use transition_control.

Requires `controls.control.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the control to update. |
| `name` | `string` | - | Control name, e.g. 'Multi-factor authentication on remote access'. |
| `description` | `string` | - | How the control operates: what is done, by whom, on what (required). |
| `theme` | `string` | - | ISO/IEC 27002:2022 theme (default 'technological'). |
| `nature` | `string` | - | Control type attribute (default 'preventive'). |
| `automation` | `string` | - | How the control is operated (default 'manual'). |
| `owner_id` | `string` | - | UUID of the accountable owner (receives the failed-test notifications). Use list_users. |
| `implemented_on` | `string` | - | Date the control started operating (ISO 8601 date), never in the future. Stamped with today when declared implemented without one (RG-CTL-02). |
| `scope_ids` | `array` | - | Scopes of the control (within your own). Its tests and runs inherit them. |
| `requirement_ids` | `array` | - | Requirements the control satisfies, from any framework. Use list_requirements. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `risk_ids` | `array` | - | Risks the control treats. Use list_risks. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `treatment_plan_ids` | `array` | - | Risk treatment plans that create or reinforce the control. Use list_risk_treatment_plans. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `pacs_measure_ids` | `array` | - | EBIOS RM PACS measures that create or reinforce the control. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `support_asset_ids` | `array` | - | Support assets the control applies to. Use list_support_assets. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `objective_ids` | `array` | - | Objectives the control contributes to. Use list_objectives. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |
| `policy_ids` | `array` | - | Documents (policies, procedures, standards) that describe the control. Use list_policys. Only targets within your scopes and in a linkable lifecycle step are accepted (RG-CTL-04); the full list replaces the current links. |

## `update_control_test`

Update a control test. Changing the frequency or the first due date recomputes the derived next due date. The control cannot change once the test has runs. The lifecycle step is not writable: use transition_control_test.

Requires `controls.test.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the test to update. |
| `control_id` | `string` | - | UUID of the control this test belongs to (not a retired one). Cannot change once the test has runs. Use list_controls. |
| `name` | `string` | - | Test name, e.g. 'Quarterly sample of remote logins'. |
| `objective` | `string` | - | What the test establishes (design, operating effectiveness). |
| `method` | `string` | - | Test method (default 'inspection'). |
| `procedure` | `string` | - | The steps the tester follows. Required to activate the test (RG-CTL-06). |
| `acceptance_criteria` | `string` | - | What a pass looks like. Required to activate the test (RG-CTL-06). |
| `frequency_months` | `integer` | - | Interval between two runs in months, 1 to 36 (default 12). Drives the next due date. |
| `tester_id` | `string` | - | UUID of the default performer of the runs, who receives the due reminders. Use list_users. |
| `first_due_date` | `string` | - | Due date of the first run (ISO 8601 date). Defaults to the activation date. |

## `update_control_test_run`

Update a run while it is in progress (draft). From 'in_review' on its content (performer, date, period, sample, result, observations) is frozen and any change is refused (RG-CTL-09). The test a run belongs to never changes.

Requires `controls.test.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the run to update. |
| `performed_by_id` | `string` | - | UUID of the person who performed the test. Defaults to the test's tester, else the caller. That person can never validate the run (RG-CTL-11). |
| `performed_on` | `string` | - | Date of the test (ISO 8601 date), never in the future. Defaults to today. |
| `period_start` | `string` | - | Start of the period the test covers (ISO 8601 date). |
| `period_end` | `string` | - | End of the period the test covers (ISO 8601 date), between period_start and performed_on (RG-CTL-10). |
| `sample_description` | `string` | - | Population and sample tested, e.g. '25 of 1,240 remote logins, March'. |
| `result` | `string` | - | Outcome against the acceptance criteria. Required to submit (RG-CTL-10). |
| `observations` | `string` | - | What was found. Required to submit a partial or failed result (RG-CTL-10); becomes the description of a raised finding. |

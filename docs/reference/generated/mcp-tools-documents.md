<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Documents

Input schemas for the 33 `documents` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `acknowledgement_campaign_allowed_transitions`

List the lifecycle transitions the caller may perform on a acknowledgement campaign from its current state.

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `add_campaign_newcomers`

Re-resolve the audience of a running acknowledgement campaign (RG-DOC-15): creates a pending row, and sends the request, to every user, group member or role assignee who has no row yet. Existing rows are never touched. Recorded in the campaign history.

Requires `documents.acknowledgement.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `campaign_id` | `string` | yes | UUID of the running campaign. Use list_acknowledgement_campaigns. |

## `batch_create_acknowledgement_campaigns`

Create or upsert several draft acknowledgement campaigns in one call (max 500). Every policy_version_id must be within the caller's scopes, or nothing is created.

Requires `documents.acknowledgement.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Campaign objects: name, policy_version_id, due_date (required), message, statement, scope_ids, audience_user_ids, audience_group_ids, audience_role_ids. |
| `match_on` | `array` | - | Optional business key (writable field names) used to find an existing campaign to update. |

## `batch_create_policy_versions`

Create or upsert several draft document versions in one call (max 500). Every policy_id must be a document within the caller's scopes, or nothing is created. Pass 'match_on' (e.g. ["policy_id", "version_label"]) to update matching drafts instead of duplicating them; a submitted version refuses any content change.

Requires `documents.policy.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Version objects: policy_id, version_label (required), content (HTML), change_summary, effective_from. |
| `match_on` | `array` | - | Optional business key (writable field names) used to find an existing version to update. |

## `batch_create_policys`

Create or upsert multiple policys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `documents.policy.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of policy objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_acknowledgement_campaign`

Create a draft acknowledgement campaign asking an audience (users, groups, roles) to confirm they have read one version of a document. Nothing is sent until the campaign is launched with transition_acknowledgement_campaign(target_state='running'), which requires the version to be in force and resolves the audience once into one row per person.

Requires `documents.acknowledgement.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Campaign name, e.g. 'Acceptable use charter 2.0 : all staff'. |
| `policy_version_id` | `string` | yes | UUID of the version to acknowledge. It must be in force when the campaign is launched. Use get_policy_in_force or list_policy_versions. |
| `message` | `string` | - | Message shown to each addressee above the content. |
| `statement` | `string` | - | Sentence each addressee confirms (max 500). {title} and {label} are replaced by the document title and version label. Defaults to the standard statement. |
| `due_date` | `string` | yes | Acknowledgement deadline (ISO 8601 date). Drives reminders and the calendar. |
| `scope_ids` | `array` | - | Scopes of the campaign. Defaults to the document's scopes when omitted. |
| `audience_user_ids` | `array` | - | Named addressees (user UUIDs). Use list_users. |
| `audience_group_ids` | `array` | - | Groups whose active members are addressed at launch. Use list_groups. |
| `audience_role_ids` | `array` | - | Roles whose assigned users are addressed at launch. Use list_roles. |

## `create_policy`

Create a new policy

Requires `documents.policy.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes | Document title, e.g. 'Access control policy'. |
| `document_type` | `string` | - | Kind of governing document (default 'policy'). |
| `summary` | `string` | - | One-paragraph purpose, shown in lists and on the Trust Center. |
| `classification` | `string` | - | Data classification of the document (default 'internal'). A Trust Center publication requires 'public'. |
| `parent_id` | `string` | - | UUID of the document this one implements (a procedure under a policy). No cycle allowed. Use list_policys. |
| `owner_id` | `string` | - | UUID of the accountable owner, who receives the review reminders. Use list_users. |
| `approver_id` | `string` | - | UUID of the expected approver of new versions (informative: the approval is whoever performs the approve transition). Use list_users. |
| `review_frequency_months` | `integer` | - | Review cycle in months, 1 to 60 (default 12). |
| `next_review_override` | `string` | - | Explicit next review date (ISO 8601 date), overriding the date derived from the version in force. |
| `scope_ids` | `array` | - | Scopes the document governs. Its versions and acknowledgement rows inherit them. |
| `linked_requirement_ids` | `array` | - | Requirements the document answers (A.5.1, clause 5.2, ...). Use list_requirements. |
| `applies_to_role_ids` | `array` | - | Roles the document is addressed to (also the default audience of a campaign). Use list_roles. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_policy_version`

Create a draft version of a document. Prefer new_policy_version, which proposes the next label and copies the content of the version in force. The PDF is attached through the web form only.

Requires `documents.policy.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_id` | `string` | yes | UUID of the document. Use list_policys. |
| `version_label` | `string` | yes | Label, unique per document, e.g. '1.0'. |
| `content` | `string` | - | The policy text (HTML rich text) |
| `change_summary` | `string` | - | What changed since the previous version and why (required to submit from the second version on). |
| `effective_from` | `string` | - | Effective date (ISO 8601 date), never in the future. Defaults to the approval date. |

## `delete_acknowledgement_campaign`

Delete a acknowledgement campaign

Requires `documents.acknowledgement.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_policy`

Delete a policy

Requires `documents.policy.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_policy_version`

Delete a policy version

Requires `documents.policy.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `excuse_policy_acknowledgement`

Excuse a pending acknowledgement row (a leaver, a long absence) with a mandatory reason (RG-DOC-19). The row leaves the completion rate's denominator and keeps its history; it can never be changed again.

Requires `documents.acknowledgement.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `acknowledgement_id` | `string` | yes | UUID of the pending row. Use list_policy_acknowledgements. |
| `reason` | `string` | yes | Why this person is excused (mandatory). |

## `get_acknowledgement_campaign`

Get a acknowledgement campaign by ID

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_acknowledgement_campaign_history`

Return the change history of a acknowledgement campaign: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the acknowledgement campaign |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_campaign_progress`

Read the progress of an acknowledgement campaign: rows by status (pending, acknowledged, excused, expired, total) and the completion rate, an integer percentage computed as acknowledged / (all rows - excused rows) (RG-DOC-19), frozen once the campaign closes.

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `campaign_id` | `string` | yes | UUID of the campaign. Use list_acknowledgement_campaigns. |

## `get_policy`

Get a policy by ID

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_policy_history`

Return the change history of a policy: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the policy |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_policy_in_force`

Read the version of a document that is currently in force: its full content, label, approval (who approved it and when), effective date and PDF integrity hash, plus the document's next review date. 'version_in_force' is null when the document has none (never approved, withdrawn or retired).

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_id` | `string` | yes | UUID of the document. Use list_policys. |

## `get_policy_version`

Get one document version by ID with its full rich-text content, change summary, approval (who, when, effective from), supersession, and the SHA-256 and download URL of its PDF when one is attached. The PDF bytes themselves are not returned.

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_policy_version_history`

Return the change history of a policy version: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the policy version |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `list_acknowledgement_campaigns`

List acknowledgement campaigns with optional search and filters

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `policy_version_id` | `string` | - | Filter by policy_version_id |

## `list_policy_versions`

List policy versions with optional search and filters

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `policy_id` | `string` | - | Filter by policy_id |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `version_label` | `string` | - | Filter by version_label |

## `list_policys`

List policys with optional search and filters

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `document_type` | `string` | - | Filter by document_type |
| `classification` | `string` | - | Filter by classification |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `owner_id` | `string` | - | Filter by owner_id |
| `parent_id` | `string` | - | Filter by parent_id |

## `new_policy_version`

Draft the next version of a document from its version in force (RG-DOC-05): proposes the next label (minor: 1.2 -> 1.3, major: 1.2 -> 2.0), copies the in-force content and PDF into a new draft, and leaves the change summary empty (write it before submitting). On a document with no version yet it drafts 1.0. Then edit it with update_policy_version and submit it with transition_policy_version(target_state='in_review').

Requires `documents.policy.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_id` | `string` | yes | UUID of the document. Use list_policys. |
| `bump` | `string` | - | Label increment (default 'minor'). |

## `policy_allowed_transitions`

List the lifecycle transitions the caller may perform on a policy from its current state.

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `policy_version_allowed_transitions`

List the lifecycle transitions the caller may perform on a policy version from its current state.

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `record_policy_review`

Record that an active document was reviewed and needs no change (RG-DOC-13): stamps the review date and reviewer, recomputes the next review date from today, and records the comment in the document history. Closes a review cycle without issuing a new version.

Requires `documents.policy.approve`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_id` | `string` | yes | UUID of the active document. Use list_policys. |
| `comment` | `string` | - | What was reviewed and why nothing changes (kept in the history). |

## `transition_acknowledgement_campaign`

Change the lifecycle state of a acknowledgement campaign (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `documents.acknowledgement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the acknowledgement campaign |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_policy`

Change the lifecycle state of a policy (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the policy |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_policy_version`

Change the lifecycle state of a policy version (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `documents.policy.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the policy version |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_acknowledgement_campaign`

Update an acknowledgement campaign. Everything is editable in draft; once launched, the target version, the statement and the audience are fixed (RG-DOC-15) and only the name, message, due date and scopes may change.

Requires `documents.acknowledgement.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the campaign to update. |
| `name` | `string` | - | Campaign name, e.g. 'Acceptable use charter 2.0 : all staff'. |
| `policy_version_id` | `string` | - | UUID of the version to acknowledge. It must be in force when the campaign is launched. Use get_policy_in_force or list_policy_versions. |
| `message` | `string` | - | Message shown to each addressee above the content. |
| `statement` | `string` | - | Sentence each addressee confirms (max 500). {title} and {label} are replaced by the document title and version label. Defaults to the standard statement. |
| `due_date` | `string` | - | Acknowledgement deadline (ISO 8601 date). Drives reminders and the calendar. |
| `scope_ids` | `array` | - | Scopes of the campaign. Defaults to the document's scopes when omitted. |
| `audience_user_ids` | `array` | - | Named addressees (user UUIDs). Use list_users. |
| `audience_group_ids` | `array` | - | Groups whose active members are addressed at launch. Use list_groups. |
| `audience_role_ids` | `array` | - | Roles whose assigned users are addressed at launch. Use list_roles. |

## `update_policy`

Update an existing policy

Requires `documents.policy.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `title` | `string` | - | Document title, e.g. 'Access control policy'. |
| `document_type` | `string` | - | Kind of governing document (default 'policy'). |
| `summary` | `string` | - | One-paragraph purpose, shown in lists and on the Trust Center. |
| `classification` | `string` | - | Data classification of the document (default 'internal'). A Trust Center publication requires 'public'. |
| `parent_id` | `string` | - | UUID of the document this one implements (a procedure under a policy). No cycle allowed. Use list_policys. |
| `owner_id` | `string` | - | UUID of the accountable owner, who receives the review reminders. Use list_users. |
| `approver_id` | `string` | - | UUID of the expected approver of new versions (informative: the approval is whoever performs the approve transition). Use list_users. |
| `review_frequency_months` | `integer` | - | Review cycle in months, 1 to 60 (default 12). |
| `next_review_override` | `string` | - | Explicit next review date (ISO 8601 date), overriding the date derived from the version in force. |
| `scope_ids` | `array` | - | Scopes the document governs. Its versions and acknowledgement rows inherit them. |
| `linked_requirement_ids` | `array` | - | Requirements the document answers (A.5.1, clause 5.2, ...). Use list_requirements. |
| `applies_to_role_ids` | `array` | - | Roles the document is addressed to (also the default audience of a campaign). Use list_roles. |

## `update_policy_version`

Update a document version. While the version is a draft, its label, content, change summary and effective date are editable. From 'in_review' onward the content, label and change summary are frozen (RG-DOC-02) and any change to them is refused. The document a version belongs to never changes.

Requires `documents.policy.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the version to update. |
| `version_label` | `string` | - | Label, unique per document (draft only). |
| `content` | `string` | - | The policy text (draft only) (HTML rich text) |
| `change_summary` | `string` | - | What changed and why (draft only). |
| `effective_from` | `string` | - | Effective date (ISO 8601 date), never in the future. |

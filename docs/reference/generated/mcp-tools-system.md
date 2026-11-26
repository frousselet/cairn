<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : System and administration

Input schemas for the 19 `system` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `batch_create_mcp_skills`

Create or upsert multiple mcp skills in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `system.mcp_skill.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of mcp skill objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_mcp_skill`

Create a new mcp skill

Requires `system.mcp_skill.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Skill name : 1 to 64 lowercase letters, digits and hyphens (e.g. supplier-onboarding). The name of a skill Cairn ships (working-with-cairn, iso27005-risk-analysis, compliance-assessment) replaces it once validated. |
| `description` | `string` | yes | What the skill does and when an agent should use it (at most 1024 characters). |
| `body` | `string` | - | The instructions, in Markdown : the steps the agent follows and the tools it calls. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_user`

Provision a new user via the invitation flow so it can be referenced as an owner / reviewer. No password is accepted: the account is created with an unusable password and the response returns an 'activation_url' the invitee follows to set their first credential. 'groups' are role / group names that must already exist (use list_groups). Requires the system.users.create permission.

Requires `system.users.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `email` | `string` | yes | Email address (login identifier). Must be unique. |
| `last_name` | `string` | yes | Last name (required). |
| `first_name` | `string` | - | First name. |
| `user_type` | `string` | - | Account type: 'human' (default) or 'robot' (service account). |
| `job_title` | `string` | - | Job title. |
| `department` | `string` | - | Department. |
| `phone` | `string` | - | Phone number. |
| `language` | `string` | - | Preferred UI language code, e.g. 'en' or 'fr'. |
| `groups` | `array` | - | Role / group names to assign (must already exist). |

## `delete_mcp_skill`

Delete a mcp skill

Requires `system.mcp_skill.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_company_settings`

Get the company settings (name, application name, AI assistant name, address, accent colour, whether the company logo replaces the Cairn logo)

Requires `system.config.read`.

No parameters.

## `get_group`

Get group details including permissions

Requires `system.groups.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_mcp_skill`

Get a mcp skill by ID

Requires `system.mcp_skill.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_mcp_skill_history`

Return the change history of a mcp skill: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `system.mcp_skill.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the mcp skill |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_user`

Get detailed information about a user

Requires `system.users.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `list_access_logs`

List access logs (authentication events)

Requires `system.audit_trail.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `event_type` | `string` | - | Filter by event type |
| `user_id` | `string` | - | Filter by user ID |

## `list_assistant_feedback`

List user feedback on Ask Cairn answers (thumbs up/down and optional comment), with the original question, language and the LLM response. Read-only; for quality analysis. Feedback already marked corrected is excluded unless include_resolved=true.

Requires `system.assistant_feedback.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `rating` | `string` | - | Filter by rating: 'up' or 'down' |
| `language` | `string` | - | Filter by interface language code |
| `provider` | `string` | - | Filter by LLM provider |
| `user_id` | `string` | - | Filter by user ID |
| `include_resolved` | `boolean` | - | Include feedback already marked corrected (default false) |

## `list_groups`

List all groups

Requires `system.groups.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_mcp_skills`

List mcp skills with optional search and filters

Requires `system.mcp_skill.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_permissions`

List all available permissions

Requires `system.groups.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `module` | `string` | - | Filter by module (context, assets, compliance, risks, system) |

## `list_users`

List users with optional search

Requires `system.users.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `is_active` | `boolean` | - | Filter by active status |

## `mcp_skill_allowed_transitions`

List the lifecycle transitions the caller may perform on a mcp skill from its current state.

Requires `system.mcp_skill.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `transition_mcp_skill`

Change the lifecycle state of a mcp skill (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `system.mcp_skill.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the mcp skill |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_company_settings`

Update company settings (name, application name, AI assistant name, address, accent colour, and/or whether the company logo replaces the Cairn logo)

Requires `system.config.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | Company name |
| `app_name` | `string` | - | Custom application name shown in the sidebar and tab titles (defaults to Cairn when empty) |
| `assistant_name` | `string` | - | Custom name for the AI assistant shown in the command palette, its answers and the sidebar (defaults to Ask Cairn when empty) |
| `address` | `string` | - | Company address (multi-line) |
| `accent_color` | `string` | - | Accent colour as a 6-digit hex code (e.g. #1E3A8A) used throughout the app; empty string resets to the Cairn navy |
| `use_logo_as_app_brand` | `boolean` | - | When true, the company logo replaces the Cairn logo across the application (sidebar, page headers); the About dialog always keeps the Cairn logo. Requires a company logo to be set. |

## `update_mcp_skill`

Update an existing mcp skill

Requires `system.mcp_skill.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | Skill name : 1 to 64 lowercase letters, digits and hyphens (e.g. supplier-onboarding). The name of a skill Cairn ships (working-with-cairn, iso27005-risk-analysis, compliance-assessment) replaces it once validated. |
| `description` | `string` | - | What the skill does and when an agent should use it (at most 1024 characters). |
| `body` | `string` | - | The instructions, in Markdown : the steps the agent follows and the tools it calls. |

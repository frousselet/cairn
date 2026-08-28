<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : System and administration

Input schemas for the 10 `system` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

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

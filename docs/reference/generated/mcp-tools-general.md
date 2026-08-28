<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : General

Input schemas for the 14 `general` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `ask_assistant`

Ask Cairn's natural-language assistant a read-only question about GRC data (e.g. 'Which decisions were made at the last management review?'). Requires the optional AI assistant to be enabled (AI_ASSISTANT_ENABLED). The answer cites real records; data access enforces the caller's permissions.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `question` | `string` | yes | Natural-language question |
| `language` | `string` | - | ISO language code for the answer (default en) |

## `create_saved_filter`

Save a named list filter for the current user. `query` is the list's filter query string; `view_key` is the list key (e.g. context.issue).

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `view_key` | `string` | yes | List key, e.g. context.issue |
| `name` | `string` | yes | Filter name |
| `query` | `string` | - | Filter query string |
| `is_shared` | `boolean` | - | Share with everyone (default false) |

## `delete_saved_filter`

Delete one of the current user's saved list filters by id.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_dashboard_layout`

Get the currently authenticated user's home-dashboard widget layout (ordered list of {key, id, size, visible, zone, params}) and the catalogue of available widgets with their allowed sizes. `id` is the widget type and `key` is the per-instance id. A size is a 'WxH' tile token: width W in 1..4 quarter-columns (1=1/4 .. 4=full width) by height H in 1..4 fixed row units, e.g. '2x1' or '4x2'. A widget with `multiple: true` (e.g. 'indicator') can appear several times, each instance carrying its own `params` (the indicator widget takes `{indicator: <id>, show_chart: bool}`).

No parameters.

## `get_me`

Get information about the currently authenticated user, including capability flags: 'can_override_import_dates' (may set created_at / updated_at on import) and 'can_create_users'.

No parameters.

## `help`

Get usage documentation for the Cairn MCP server. Call without arguments for the full guide, or with a topic for focused help. Topics: context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `topic` | `string` | - | Optional topic: context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users |

## `kanban_board`

Get the unified To do / Doing / Done board aggregating action plans, treatment actions, audits and risk assessments (read-only)

No parameters.

## `list_dependencies`

List the third-party open source components this Cairn instance is built on : name, resolved version, official repository URL and what each one is used for. Same registry as the About modal. Optionally filtered by group.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `group` | `string` | - | Restrict to one group: 'backend' (Python), 'frontend' (JavaScript, CSS, fonts) or 'development' (test and lint tooling). |

## `list_notifications`

List the currently authenticated user's in-app notifications (most recent first), with the unread count. Set unread_only=true to only return unread notifications.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `unread_only` | `boolean` | - | Only unread notifications. |
| `limit` | `integer` | - | Max results (default 20, max 100). |

## `list_saved_filters`

List the current user's saved list filters (own + shared). Optional view_key (e.g. 'context.issue') narrows to one list.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `view_key` | `string` | - | List key, e.g. context.issue |

## `mark_all_notifications_read`

Mark all of the authenticated user's unread notifications as read.

No parameters.

## `mark_notification_read`

Mark one of the authenticated user's notifications as read.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the notification |

## `update_dashboard_layout`

Replace the currently authenticated user's home-dashboard widget layout. Pass `layout` as an ordered list of {key, id, size, visible, zone, params} instances; use get_dashboard_layout first to discover widget ids, allowed sizes and which widgets are 'multiple'. Give each instance of a 'multiple' widget a distinct key. The payload is sanitised against the registry.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `layout` | `array` | yes | Ordered widget instances {key, id, size, visible, zone, params}. |

## `update_me`

Update the currently authenticated user's profile (self-service). Accepts first_name, last_name, phone, language, timezone, theme_preference.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `first_name` | `string` | - | First name. |
| `last_name` | `string` | - | Last name. |
| `phone` | `string` | - | Phone number. |
| `language` | `string` | - | Interface language code (empty for auto, 'fr', 'en'). |
| `timezone` | `string` | - | IANA timezone, e.g. 'Europe/Paris'. |
| `theme_preference` | `string` | - | Display theme. 'system' follows the OS preference. |

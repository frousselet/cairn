# Activity

`context.models.activity.Activity`

Represents a business activity or process of the organization.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `reference` | string | required, unique | Reference code (e.g. ACT-001) |
| `name` | string | required, max 255 | Activity name |
| `description` | text | optional | Detailed description |
| `type` | enum | required | `core_business`, `support`, `management` |
| `criticality` | enum | required | `low`, `medium`, `high`, `critical` |
| `owner_id` | relation | FK → User, required | Activity owner |
| `parent_activity_id` | relation | FK → Activity, optional | Parent activity (hierarchy) |
| `related_stakeholders` | relation | M2M → Stakeholder | Stakeholders involved |
| `related_objectives` | relation | M2M → Objective | Contributing objectives |
| `linked_assets` | relation | M2M → EssentialAsset | Essential assets supporting the activity (Assets module) |
| `status` | enum | required | `active`, `inactive`, `planned` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

An activity follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed
on its page.

**Creation** asks for the name, the type, the criticality, the owner (whoever
creates it, unless they say otherwise), the description and the scopes (not
asked with a single scope). The user lands on the page of the new activity.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (name, type,
criticality, owner, description, scopes, tags, status) and relations (the
activity it is a part of, the objectives it helps to reach, the stakeholders
it serves). The card also lists its sub-activities and the essential assets
it relies on, which are set from those records.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Say what it covers | `description` holds a text | no |
| Link the objectives it helps to reach | `related_objectives` holds an objective | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_activity` tool as well.

**Relations.** `related_objectives` and `related_stakeholders` were set over
the REST API, the MCP server and the administration only. A picker offers
what its lifecycle makes linkable, plus what the activity already holds
(`linkable_or_linked`), within the user's scopes; an activity is not offered
as its own parent. The page names a linked record only to a reader whose
scopes reach it.

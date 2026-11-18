# AssetGroup

`assets.models.group.AssetGroup`

Grouping of support assets into a logical batch (e.g. "Production servers") to facilitate management and risk assessment.

Allows support assets to be grouped into a logical batch (e.g. "Production servers", "Paris site workstations") to facilitate management and risk assessment.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `name` | string | required, max 255 | Group name |
| `description` | text | optional | Group description |
| `type` | enum | required | Same typology as SupportAsset.type |
| `members` | relation | M2M → SupportAsset | Member support assets |
| `owner_id` | relation | FK → User, optional | Group owner |
| `status` | enum | required | `active`, `inactive` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

An asset group follows the [usability standard](../../sdk/usability-standard.md).

**Creation** asks for the name, the type, the owner (the creator by default),
the description and the scopes (not asked with a single scope). The user lands
on the page of the new group.

**The page** shows two cards, each with its own *Edit* : identity (name, type,
status, owner, description, scopes, tags) and **members**. The members card
opens the dialog that picks the support assets of the group, among those the
user may select : the interface used to list the members without offering any
way to choose them (the REST API and the MCP server alone could).

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Add the support assets it gathers | It has a member | no |


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

# Group

`accounts.models.group.Group`

Represents a group of permissions. Access rights are granted exclusively through groups, never directly to a user.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `name` | string | required, unique, max 255 | Group name |
| `description` | text | optional | Description of the group and its purpose |
| `is_system` | boolean | required, default false | System group (not editable, not deletable) |
| `permissions` | relation | M2M → Permission | Associated permissions |
| `users` | relation | M2M → User | Member users |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

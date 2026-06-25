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

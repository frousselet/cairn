# AssetDependency

`assets.models.dependency.AssetDependency`

Dependency relationship between an essential asset and a support asset, the vector for inheriting the CIA security needs.

Represents the dependency link between an essential asset and a support asset. It is through this relationship that the CIA security needs are inherited by support assets.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `essential_asset_id` | relation | FK → EssentialAsset, required | Source essential asset |
| `support_asset_id` | relation | FK → SupportAsset, required | Target support asset |
| `dependency_type` | enum | required | `runs_on`, `stored_in`, `transmitted_by`, `managed_by`, `hosted_at`, `protected_by`, `other` |
| `criticality` | enum | required | `low`, `medium`, `high`, `critical` |
| `description` | text | optional | Description of the dependency relationship |
| `is_single_point_of_failure` | boolean | required, default false | Single point of failure |
| `redundancy_level` | enum | optional | `none`, `partial`, `full` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Uniqueness constraint: the pair (`essential_asset_id`, `support_asset_id`) must be unique.

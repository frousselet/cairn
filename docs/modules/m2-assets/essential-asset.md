# EssentialAsset

`assets.models.essential_asset.EssentialAsset`

Business process or type of information essential to the organization, the compromise of which would have a significant impact.

Represents a business process or a type of information essential to the organization, the compromise of which would have a significant impact.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `reference` | string | required, unique | Reference code (e.g. BE-001) |
| `name` | string | required, max 255 | Essential asset name |
| `description` | text | optional | Detailed description |
| `type` | enum | required | `business_process`, `information` |
| `category` | enum | required | See list below |
| `owner_id` | relation | FK → User, required | Essential asset owner |
| `custodian_id` | relation | FK → User, optional | Custodian / operational manager |
| `confidentiality_level` | enum | required | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `integrity_level` | enum | required | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `availability_level` | enum | required | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `confidentiality_justification` | text | optional | Justification of the confidentiality level |
| `integrity_justification` | text | optional | Justification of the integrity level |
| `availability_justification` | text | optional | Justification of the availability level |
| `max_tolerable_downtime` | string | optional | Maximum tolerable downtime (MTD) |
| `recovery_time_objective` | string | optional | Recovery time objective (RTO) |
| `recovery_point_objective` | string | optional | Recovery point objective (RPO) |
| `data_classification` | enum | optional | `public`, `internal`, `confidential`, `restricted`, `secret` |
| `personal_data` | boolean | required, default false | Contains personal data |
| `personal_data_categories` | json | optional | Personal data categories (GDPR) |
| `regulatory_constraints` | text | optional | Specific regulatory constraints |
| `related_activities` | relation | M2M → Activity | Associated business activities (Module 1) |
| `supporting_assets` | relation | M2M → SupportAsset (via AssetDependency) | Associated support assets |
| `status` | enum | required | `identified`, `active`, `under_review`, `decommissioned` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Essential asset categories (values of `category`):**

- *Type `business_process`:* `core_process`, `support_process`, `management_process`
- *Type `information`:* `strategic_data`, `operational_data`, `personal_data`, `financial_data`, `technical_data`, `legal_data`, `research_data`, `commercial_data`

> Note: The categories must be configurable by the administrator.

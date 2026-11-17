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
| `confidentiality_level` | enum | optional, no default | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4). Empty : not assessed yet (RV-07) |
| `integrity_level` | enum | optional, no default | Same scale. Empty : not assessed yet |
| `availability_level` | enum | optional, no default | Same scale. Empty : not assessed yet |
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

## Creation, completion, completeness

An essential asset follows the
[usability standard](../../sdk/usability-standard.md) : it is created short,
then completed on its page.

**Creation** asks for the name, the category (grouped under the type it
belongs to : the type follows from it, RS-01), the owner (the creator by
default), the description and the scopes. With a single scope there is nothing
to choose : the asset is filed under it. The security needs are **not** asked :
they start empty (RV-07). The user lands on the page of the new asset.

**The page** lists what the asset still needs (below) and shows one card per
section of its form, each with its own dialog : identity, people, security
needs (the three questions, each with its justification), business continuity,
data and regulation, activities and review. A level is shown with its word
(*High*), an empty one reads *Not assessed*.

**Completeness** (`EssentialAsset.COMPLETENESS`, rule RS-10) :

| Key | The asset... | Tested on | Holds the lifecycle |
|---|---|---|---|
| `security_needs` | has its security needs assessed | the three levels are set | yes |
| `description` | says what it is used for | `description` is not empty | no (advised) |
| `support_assets` | has the support assets it relies on | a dependency exists | no (advised) |
| `continuity` | says how long the business can do without it | one of `max_tolerable_downtime`, `recovery_time_objective`, `recovery_point_objective` | no (advised) |

The REST API serves it with a single asset
(`completeness : {complete, can_advance, missing : [{key, label, blocking}]}`)
and the MCP `get_essential_asset` tool reports the same.

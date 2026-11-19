# SupportAsset

`assets.models.support_asset.SupportAsset`

Technical, human or physical asset that supports the essential assets and on which vulnerabilities can be exploited.

Represents a technical, human or physical asset that supports the essential assets and on which vulnerabilities can be exploited.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `reference` | string | required, unique | Reference code (e.g. BS-001) |
| `name` | string | required, max 255 | Support asset name |
| `description` | text | optional | Detailed description |
| `type` | enum | required | `hardware`, `software`, `network`, `person`, `service`, `paper`. The web form does not ask for it : the category names it (RS-02) |
| `category` | enum | required | See list below |
| `owner_id` | relation | FK → User, required | Support asset owner |
| `custodian_id` | relation | FK → User, optional | Custodian / operational manager |
| `location` | string | optional | Physical location |
| `manufacturer` | string | optional | Manufacturer / vendor |
| `model` | string | optional | Model / version |
| `serial_number` | string | optional | Serial number |
| `version` | string | optional | Version (software, firmware) |
| `ip_address` | string | optional | IP address (if applicable) |
| `hostname` | string | optional | Hostname (if applicable) |
| `operating_system` | string | optional | Operating system |
| `acquisition_date` | date | optional | Acquisition date |
| `end_of_life_date` | date | optional | End-of-life / end-of-support date |
| `warranty_expiry_date` | date | optional | Warranty expiry date |
| `supplier_id` | relation | FK → Supplier, optional | Associated supplier (Suppliers module) |
| `contract_reference` | string | optional | Associated contract reference |
| `inherited_confidentiality` | enum | calculated, may be empty | Highest assessed level of the essential assets that rely on it (RV-03). Empty : none of them is assessed, or nothing relies on it (RV-07) |
| `inherited_integrity` | enum | calculated, may be empty | Same rule |
| `inherited_availability` | enum | calculated, may be empty | Same rule |
| `exposure_level` | enum | optional | `internal`, `exposed`, `internet_facing`, `dmz` |
| `environment` | enum | optional | `production`, `staging`, `development`, `test`, `disaster_recovery` |
| `essential_assets` | relation | M2M → EssentialAsset (via AssetDependency) | Supported essential assets |
| `parent_asset_id` | relation | FK → SupportAsset, optional | Parent support asset (composition) |
| `controls` | relation | reverse M2M ← [Control](../m8-controls/control.md) `support_assets` | Security controls applied to the asset |
| `status` | enum | required | `in_stock`, `deployed`, `active`, `under_maintenance`, `decommissioned`, `disposed` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Support asset categories (values of `category`):**

- *`hardware`:* `server`, `workstation`, `laptop`, `mobile_device`, `network_equipment`, `storage`, `peripheral`, `iot_device`, `removable_media`, `other_hardware`
- *`software`:* `operating_system`, `database`, `application`, `middleware`, `security_tool`, `development_tool`, `saas_application`, `other_software`
- *`network`:* `lan`, `wan`, `wifi`, `vpn`, `internet_link`, `firewall_zone`, `dmz`, `other_network`
- *`person`:* `internal_staff`, `contractor`, `external_provider`, `administrator`, `developer`, `other_person`
- *`site`:* `datacenter`, `office`, `remote_site`, `cloud_region`, `other_site`
- *`service`:* `cloud_service`, `hosting_service`, `managed_service`, `telecom_service`, `outsourced_service`, `other_service`
- *`paper`:* `archive`, `printed_document`, `form`, `other_paper`

> Note: The categories must be configurable by the administrator.

## Creation, completion, completeness

A support asset follows the
[usability standard](../../sdk/usability-standard.md) : it is created short,
then completed on its page.

**Creation** asks for the name, the category (grouped under the type it
belongs to : the type follows from it, RS-02), the owner (the creator by
default), the description and the scopes. With a single scope there is nothing
to choose : the asset is filed under it. The user lands on the page of the new
asset.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity, people, technical
specifications, environment and exposure, dates and contract, relations. The
card of the inherited security needs is not edited : it shows the levels with
their words and the essential assets they come from, or says that no essential
asset relies on the asset yet, in which case its needs are *not known*.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Link the essential assets | It has a dependency (done on the dependencies page) | no |
| Set the environment and the exposure level | `environment` and `exposure_level` are set | no |
| Set the end of life date | `end_of_life_date` is set | no |

Nothing holds the lifecycle of a support asset back : the three lines are
advice. The REST API returns them in `completeness` on a single record, and
the MCP `get_support_asset` tool as well.

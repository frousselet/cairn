# Framework

`compliance.models.framework.Framework`

Normative, legal, regulatory, contractual or internal framework with which the organization must or chooses to comply.

## Entity: Framework

Represents a normative, legal, regulatory, contractual or internal framework with which the organization must or chooses to comply.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `reference` | string | required, unique | Reference code (e.g. REF-001) |
| `name` | string | required, max 255 | Name of the framework (e.g. "ISO 27001:2022") |
| `short_name` | string | optional, max 50 | Abbreviation (e.g. "ISO 27001") |
| `description` | text | optional | Description of the framework |
| `type` | enum | required | `standard`, `law`, `regulation`, `contract`, `internal_policy`, `industry_framework`, `other` |
| `category` | enum | required | See list below |
| `version` | string | optional | Version of the framework (e.g. "2022") |
| `publication_date` | date | optional | Official publication date |
| `effective_date` | date | optional | Date of entry into force |
| `expiry_date` | date | optional | Expiry or repeal date |
| `issuing_body` | string | optional | Issuing body (e.g. "ISO", "European Parliament") |
| `jurisdiction` | string | optional | Applicable jurisdiction (e.g. "France", "European Union", "International") |
| `url` | string | optional, URL format | Link to the official text |
| `is_mandatory` | boolean | required, default false | Mandatory framework (legal/regulatory constraint) |
| `is_applicable` | boolean | required, default true | Applicable to the scope |
| `applicability_justification` | text | optional | Justification of applicability or non-applicability |
| `applicability_managed_by_risks` | boolean | required, default false | Risk-driven applicability (see below) |
| `owner_id` | relation | FK → User, required | Owner of compliance tracking for this framework |
| `related_stakeholders` | relation | M2M → Stakeholder | Stakeholders behind this framework |
| `compliance_level` | decimal | calculated, 0-100 | Calculated overall compliance level (%) |
| `last_assessment_date` | date | calculated | Date of the last assessment |
| `status` | enum | required | `draft`, `active`, `under_review`, `deprecated`, `archived` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Framework categories (values of `category`):**

- `information_security` (Information security: ISO 27001, ISO 27002, etc.)
- `privacy` (Data protection: GDPR, CCPA, etc.)
- `risk_management` (Risk management: ISO 27005, ISO 31000, etc.)
- `business_continuity` (Business continuity: ISO 22301, etc.)
- `cloud_security` (Cloud security: ISO 27017, ISO 27018, SecNumCloud, etc.)
- `sector_specific` (Sector-specific regulations: NIS 2, DORA, HDS, PCI DSS, etc.)
- `it_governance` (IT governance: COBIT, ITIL, etc.)
- `quality` (Quality: ISO 9001, etc.)
- `contractual` (Contractual requirements)
- `internal` (Internal policies and procedures)
- `other`

> Note: Categories and types must be configurable by the administrator.

## Risk-driven applicability (`applicability_managed_by_risks`)

When the `applicability_managed_by_risks` option is enabled on a framework,
the applicability of each of its requirements (`Requirement.is_applicable`) is
no longer entered manually but **derived automatically from the associated risks**:

- a requirement is **applicable** as soon as at least one of its associated risks is
  in a lifecycle state **counted in reports** (active risk,
  see `core.workflow.reportable`); for the risk workflow, only the
  initial `identified` state is not counted;
- a requirement with no associated active risk is **not applicable**.

Consequences:

- The `is_applicable` and `applicability_justification` fields of the framework's
  requirements become **read-only** (UI, API, MCP): any value provided
  is ignored and the justification is filled in automatically.
- The recalculation is triggered on each association/dissociation of a risk, on
  each state change of an associated risk, on the deletion of a risk, and
  when the option is enabled (recalculation of all requirements). The
  compliance levels of the section and the framework are refreshed
  accordingly.
- Disabling the option freezes the calculated values (manual editing becomes
  possible again). When the option is disabled, the behavior is unchanged.

The `Statement of Applicability` (SoA) reflects these values directly, since
`is_applicable` remains a stored field.

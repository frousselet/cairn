# EcosystemStakeholder

`risks.models.ebios.ecosystem_stakeholder.EcosystemStakeholder`

Ecosystem stakeholder that may constitute an attack vector. Model independent from `context.Stakeholder` (ISO 9001/27001 interested parties). Reference prefix: `EECS`.

## 4.3.1 Entity: EcosystemStakeholder (Ecosystem stakeholder)

Model independent from `context.Stakeholder` (ISO 9001/27001 interested parties). Optional link via FK.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix EECS | Code (e.g. EECS-1) |
| `stakeholder_id` | relation | FK -> Stakeholder, optional | Module 1 link (if already recorded) |
| `supplier_id` | relation | FK -> Supplier, optional | Module 2 link (if a supplier) |
| `name` | string | required, max 255 | Name |
| `description` | text | optional | Description of the role in the ecosystem |
| `category` | enum | required | `supplier`, `partner`, `subcontractor`, `customer`, `regulator`, `shared_infrastructure`, `client_employee`, `other` |
| `dependency` | integer | optional, 1 to 4 | How much the organisation relies on the stakeholder : `1 - Not needed`, `2 - Useful`, `3 - Essential, with a substitute`, `4 - Essential, without a substitute` |
| `penetration` | integer | optional, 1 to 4 | How far the stakeholder reaches into the information system : from `1 - No access, or user access to workstations` to `4 - Administrator access to the infrastructure` |
| `maturity` | integer | optional, 1 to 4 | How well the stakeholder protects its own systems : from `1 - Basic rules, applied now and then` to `4 - Risks managed and reviewed` |
| `trust` | integer | optional, 1 to 4 | How sure the organisation is of its intentions : from `1 - Intentions unknown` to `4 - Intentions known, compatible with yours` |
| `threat_level` | decimal(4,2) | computed | `(dependency * penetration) / (maturity * trust)` |
| `threat_zone` | enum | computed | `control`, `monitoring`, `danger` (thresholds [see README §2.6](README.md#26-mapping-of-the-digital-threat-across-the-ecosystem)) |
| `accessible_support_assets` | M2M -> SupportAsset | optional | Accessible support assets |
| `is_attack_vector` | boolean | required, default false | Identified as an attack vector |
| `attack_vector_justification` | text | optional | Justification |
| `criteria_snapshot` | json | computed | Snapshot of the zoning thresholds |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> `threat_level` and `threat_zone` are computed in `save()` according to the formula in [README §2.6](README.md#26-mapping-of-the-digital-threat-across-the-ecosystem). The thresholds are configurable on [`RiskCriteria`](../risk-criteria.md) (JSON key `ebios_ecosystem_thresholds`).

## Creation and edition

An ecosystem stakeholder is a row of the page of workshop 3 (see [README, 8.6](README.md)).

- **Creation** asks for six fields on one screen : the name, the category (a decision, the select opens on *Choose...*) and the four ratings. A rating may wait : it reads *Not assessed*, and the threat level and its zone are computed once the four are given. The study is known from the address and is never asked.
- **The four ratings** are picked by the name of their level (`risks.constants.DependencyLevel`, `PenetrationLevel`, `CyberMaturityLevel`, `TrustLevel`). They were choices of bare numbers.
- **Edition** has two sections : *Ecosystem stakeholder* (name, category, description, the interested party or the supplier it already is in the registers, the support assets it has an access to, picked among those of the security baseline) and *Threat level* (the four ratings, and whether an attacker could pass through it, with the reason).
- `accessible_support_asset_ids` sets the support assets through the MCP tools.


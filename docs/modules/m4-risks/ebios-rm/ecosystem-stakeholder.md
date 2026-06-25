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
| `dependency` | integer | required, 1 to 4 | Dependency of the organization on the stakeholder |
| `penetration` | integer | required, 1 to 4 | Penetration of the stakeholder into the ecosystem |
| `maturity` | integer | required, 1 to 4 | Cyber maturity of the stakeholder |
| `trust` | integer | required, 1 to 4 | Trust placed in the stakeholder |
| `threat_level` | decimal(4,2) | computed | `(dependency * penetration) / (maturity * trust)` |
| `threat_zone` | enum | computed | `control`, `monitoring`, `danger` (thresholds [see README §2.6](README.md#26-mapping-of-the-digital-threat-across-the-ecosystem)) |
| `accessible_support_assets` | M2M -> SupportAsset | optional | Accessible support assets |
| `is_attack_vector` | boolean | required, default false | Identified as an attack vector |
| `attack_vector_justification` | text | optional | Justification |
| `criteria_snapshot` | json | computed | Snapshot of the zoning thresholds |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> `threat_level` and `threat_zone` are computed in `save()` according to the formula in [README §2.6](README.md#26-mapping-of-the-digital-threat-across-the-ecosystem). The thresholds are configurable on [`RiskCriteria`](../risk-criteria.md) (JSON key `ebios_ecosystem_thresholds`).

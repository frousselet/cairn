# EbiosSummary

`risks.models.ebios.ebios_summary.EbiosSummary`

Summary of the EBIOS RM assessment (workshop 5). Only one per assessment. Reference prefix: `ESUM`.

## 4.5.1 Entity: EbiosSummary (Assessment summary)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required, unique | Parent assessment |
| `reference` | string | required, unique, prefix ESUM | Code (e.g. ESUM-1) |
| `residual_risk_strategy` | text | required | Overall residual risk treatment strategy |
| `monitoring_plan` | text | optional | Monitoring and continuous improvement plan |
| `pacs_summary` | text | optional | Narrative summary of the PACS |
| `risk_mapping_before` | json | computed | Snapshot of the risk mapping before treatment |
| `risk_mapping_after` | json | computed | Snapshot of the mapping after treatment |
| `next_strategic_cycle_date` | date | optional | Next planned strategic iteration |
| `next_operational_cycle_date` | date | optional | Next planned operational iteration |
| `validated_by_id` | relation | FK -> User, optional | Executive management validator |
| `validated_at` | datetime | optional | Validation date |
| `status` | enum | required | `draft`, `in_progress`, `under_review`, `validated` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

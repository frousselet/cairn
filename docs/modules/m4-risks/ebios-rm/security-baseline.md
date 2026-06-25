# SecurityBaseline

`risks.models.ebios.security_baseline.SecurityBaseline`

Root of EBIOS RM workshop 1. Only one per assessment. Reference prefix: `EBSL`.

## 4.1.1 Entity: SecurityBaseline (Security baseline)

Root of workshop 1. Only one per assessment.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required, unique | Parent assessment |
| `reference` | string | required, unique, prefix EBSL | Code (e.g. EBSL-1) |
| `business_values` | M2M -> Activity | required | Business values retained |
| `essential_assets` | M2M -> EssentialAsset | required | Essential assets retained |
| `support_assets` | M2M -> SupportAsset | required | Support assets retained |
| `dic_summary` | text | optional | Summary of CIA security needs |
| `baseline_references` | M2M -> Framework | optional | Baseline frameworks (ISO 27002, ANSSI, NIST, etc.) |
| `status` | enum | required | `draft`, `in_progress`, `completed` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

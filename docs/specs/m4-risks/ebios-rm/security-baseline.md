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

## Edition

The security baseline is created with its assessment and edited from the page of workshop 1, one card at a time. Its form has three sections :

| Section | Fields | Card of the page |
|---|---|---|
| `studied` | `business_values`, `essential_assets`, `support_assets` | Business values and assets |
| `needs` | `dic_summary` | Security needs summary |
| `references` | `baseline_references` | Baseline references |

A new link targets a record that can be linked (lifecycle rule RG-LC-03) and that the user may reach; what the baseline already holds stays. The four relations are set through the MCP tools as well (`business_value_ids`, `essential_asset_ids`, `support_asset_ids`, `baseline_reference_ids`).

What the baseline must hold before workshop 1 is validated is declared on the progress of the workshop : see [EbiosWorkshopProgress, Completeness](workshop-progress.md#completeness).


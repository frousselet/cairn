# BaselineGap

`risks.models.ebios.baseline_gap.BaselineGap`

Gap identified between the current security posture and the expected security baseline (frameworks, good practices). Reference prefix: `EBGP`.

## 4.1.3 Entity: BaselineGap (Baseline gap)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `baseline_id` | relation | FK -> [SecurityBaseline](security-baseline.md), required | Parent baseline |
| `reference` | string | required, unique, prefix EBGP | Code (e.g. EBGP-1) |
| `reference_source` | string | required | Baseline source (e.g. "ISO 27002:2022 A.5.1", "ANSSI hygiene guide #12") |
| `linked_requirement_id` | relation | FK -> Requirement, optional | Linked compliance requirement |
| `description` | text | required | Gap description |
| `affected_support_assets` | M2M -> SupportAsset | optional | Affected support assets |
| `severity` | enum | required | `low`, `medium`, `high`, `critical` |
| `recommended_remediation` | text | optional | Recommended remediation |
| `status` | enum | required | `identified`, `accepted`, `in_remediation`, `remediated` |
| `linked_pacs_measures` | M2M -> [PACSMeasure](pacs-measure.md) | optional | PACS measures addressing the gap |
| `order` | integer | required | Display order |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

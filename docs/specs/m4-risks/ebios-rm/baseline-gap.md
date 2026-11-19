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

## Creation and edition

A baseline gap is a row of the page of workshop 1 (see [README, 8.4](README.md)).

- **Creation** asks for three fields on one screen : the reference source (the rule that is not met), the description and the severity. The severity is a decision : the select opens on *Choose...* and the default of the model is not saved for the reader. The baseline and `order` are not asked.
- **Edition** adds the linked requirement, picked among the requirements of the baseline references, the affected support assets, picked among the support assets of the baseline, and the recommended remediation. What the gap already holds stays offered.
- `affected_support_asset_ids` sets the affected support assets through the MCP tools (`create_ebios_baseline_gap`, `update_ebios_baseline_gap`).
- **Deletion** is offered while the lifecycle step of the gap is deletable (`identified`). The status of a gap is its lifecycle step; the web interface shows it and does not move it yet.


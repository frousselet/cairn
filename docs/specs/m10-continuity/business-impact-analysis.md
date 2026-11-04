# BusinessImpactAnalysis

`continuity.models.bia.BusinessImpactAnalysis`

A business impact analysis over one perimeter : which activities and essential assets are critical, how a disruption hurts over time, and how fast each must come back (ISO 22301 clause 8.2.2; ISO/IEC 27001:2022 A.5.30). It holds [entries](bia-entry.md) and is validated as a whole (RG-BCM-04 to RG-BCM-06).

File: `continuity/models/bia.py`

`ScopedModel` : `reference` (prefix **`BIAN`**), `scopes`, `tags`, history. `LIFECYCLE_NAME = "business_impact_analysis"`. `workflow_perm_namespace = "continuity.bia"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `name` | string | required, max 255 | e.g. `BIA 2026 : Voltara operations` |
| `description` | text | optional | Method, participants, assumptions |
| `owner` | relation | FK -> User, `SET_NULL`, optional | |
| `time_windows` | JSON list | default `["4h", "24h", "72h", "1w", "1m"]`, editable in draft only | Ordered windows of the impact grid; each `<n>h`, `<n>d`, `<n>w` or `<n>m` |
| `review_frequency_months` | integer | 1 to 36, default 12 | Drives `BIA_REVIEW_DUE` |
| `validated_by`, `validated_at` | | not editable | Stamped at validation |
| `superseded_by` | relation | FK -> self, `SET_NULL`, not editable | RG-BCM-06 |
| `workflow_state` | string | default `draft` | |

## Computed

- `critical_entries` : entries whose MTD is at most 24 hours.
- `next_review_date` : `validated_at` + `review_frequency_months`.

## References

- [BiaEntry](bia-entry.md), [README.md](README.md) : RG-BCM-01 to RG-BCM-06

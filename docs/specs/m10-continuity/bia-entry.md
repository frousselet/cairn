# BiaEntry

`continuity.models.bia.BiaEntry`

One assessed target of a [BIA](business-impact-analysis.md) : an activity or an essential asset, its impact grid, its recovery objectives and its dependencies. A child row : history-tracked, no lifecycle or reference of its own, editable only while the analysis is in `draft` (RG-BCM-04).

File: `continuity/models/bia.py`

Plain `models.Model` with UUID PK, `HistoricalRecords`; scopes through `analysis__scopes`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `analysis` | relation | FK -> analysis, `CASCADE` while draft | Reverse `entries` |
| `activity` | relation | FK -> `context.Activity`, `PROTECT`, optional | Exactly one of `activity` / `essential_asset` (RG-BCM-01) |
| `essential_asset` | relation | FK -> `assets.EssentialAsset`, `PROTECT`, optional | |
| `impacts` | JSON object | `{category: [score per window]}`, scores 1 to 4, non-decreasing (RG-BCM-02) | Categories `financial`, `operational`, `legal`, `reputational`, `safety` |
| `mtd_hours`, `rto_hours`, `rpo_hours` | decimal | >= 0, `rto <= mtd` (RG-BCM-03) | |
| `minimum_service_level` | text | optional | Minimum business continuity objective (MBCO) |
| `peak_periods` | text | optional | When a disruption hurts most |
| `support_assets` | M2M | `assets.SupportAsset` | Dependencies |
| `suppliers` | M2M | `assets.Supplier` | Dependencies |
| `sites` | M2M | `context.Site` | Dependencies |
| `notes` | text | optional | |
| `order` | integer | default 0 | |

`UniqueConstraint(analysis, activity)` and `(analysis, essential_asset)` (conditions on non-null).

## Computed

`worst_impact` (max score), `suggested_mtd_hours` (RG-BCM-03), `is_complete`.

## References

- [README.md](README.md) : RG-BCM-01 to RG-BCM-05

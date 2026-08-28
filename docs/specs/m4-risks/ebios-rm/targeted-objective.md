# TargetedObjective

`risks.models.ebios.targeted_objective.TargetedObjective`

Targeted objective (OV): the aim pursued by a risk source. Reference prefix: `ETOV`.

## 4.2.2 Entity: TargetedObjective (Targeted objective)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `risk_source_id` | relation | FK -> [RiskSource](risk-source.md), required | Parent SR |
| `reference` | string | required, unique, prefix ETOV | Code (e.g. ETOV-1) |
| `name` | string | required, max 255 | Title |
| `description` | text | optional | Description |
| `category` | enum | required | `lucrative`, `strategic`, `terrorist`, `ideological`, `revenge`, `ludic`, `other` |
| `targeted_essential_assets` | M2M -> EssentialAsset | optional | Targeted essential assets |
| `targeted_feared_events` | M2M -> [FearedEvent](feared-event.md) | optional | Associated feared events |
| `is_retained` | boolean | required, default true | OV retained |
| `order` | integer | required | Order |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

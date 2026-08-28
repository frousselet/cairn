# FearedEvent

`risks.models.ebios.feared_event.FearedEvent`

Characterizes a CIA breach on an essential asset together with its severity. Reference prefix: `EFER`.

## 4.1.2 Entity: FearedEvent (Feared event)

Characterizes a CIA breach on an essential asset together with its severity.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `baseline_id` | relation | FK -> [SecurityBaseline](security-baseline.md), required | Parent baseline |
| `reference` | string | required, unique, prefix EFER | Code (e.g. EFER-1) |
| `essential_asset_id` | relation | FK -> EssentialAsset, required | Essential asset concerned |
| `name` | string | required, max 255 | Short title |
| `description` | text | required | Description |
| `dic_criterion` | enum | required | `confidentiality`, `integrity`, `availability` |
| `gravity_level` | integer | required, computed/entered | Severity (RiskCriteria impact scale) |
| `gravity_justification` | text | optional | Severity justification |
| `business_impacts` | json | optional | Detailed impacts (keys: `financial`, `legal`, `reputation`, `operational`, `human`, `environmental`) |
| `criteria_snapshot` | json | computed | Snapshot of the scale at the time of entry |
| `order` | integer | required | Display order |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> Rule: for a given `essential_asset_id`, at most 3 `FearedEvent` (one per CIA criterion). Enforced by the uniqueness constraint `(baseline_id, essential_asset_id, dic_criterion)`.

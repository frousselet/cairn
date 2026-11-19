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

## Creation and edition

A targeted objective is a row of its risk source, on the page of workshop 2 (see [README, 8.5](README.md)).

- **Creation** asks for three fields on one screen : the name, the category (a decision, the select opens on *Choose...*) and the feared events the objective would cause. The risk source is known from the address and is never asked; `order` is not asked either, a new objective comes last.
- **The feared events and the essential assets** an objective targets are picked in its own study : the feared events of its security baseline, the essential assets that baseline names. The pickers used to list those of every study. What the objective already targets stays offered.
- **Edition** adds the description, the targeted essential assets and whether the objective is retained.
- `targeted_feared_event_ids` and `targeted_essential_asset_ids` set the two relations through the MCP tools.


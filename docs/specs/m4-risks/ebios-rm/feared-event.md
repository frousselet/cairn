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

## Creation and edition

A feared event is a row of the page of workshop 1 (see [README, 8.4](README.md)).

- **Creation** asks for four fields on one screen : the essential asset, the security criterion, the name and the gravity level. The baseline is known from the address and is never asked; `order` is not asked either, a new event comes last.
- **The essential asset** is picked among those of the security baseline : a feared event is about an asset of the study. The asset an event already names stays offered.
- **The gravity level** is picked by its name on the impact scale of the criteria of the assessment. No level is an answer too : it reads *Not assessed*, the model has no default.
- **Edition** shows the event whole on one screen, with its description and the justification of its gravity.
- The uniqueness of `(baseline, essential_asset, dic_criterion)` is checked by the form, which names the event that already exists : the baseline is not a field of the form, so the constraint used to be refused by the database, as a server error.
- **Deletion** is offered while the lifecycle step of the event is deletable. A refusal is a message on the page of the workshop.

`business_impacts` is written through the REST API and the MCP server only.

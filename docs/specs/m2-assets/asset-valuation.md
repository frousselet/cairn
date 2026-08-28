# AssetValuation

`assets.models.valuation.AssetValuation`

History of an essential asset's CIA ratings, allowing the evolution of security needs to be tracked over time.

Keeps the history of an essential asset's CIA ratings, allowing the evolution of security needs to be tracked over time.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `essential_asset_id` | relation | FK → EssentialAsset, required | Rated essential asset |
| `evaluation_date` | date | required | Rating date |
| `confidentiality_level` | enum | required | C level at this date |
| `integrity_level` | enum | required | I level at this date |
| `availability_level` | enum | required | A level at this date |
| `evaluated_by` | relation | FK → User, required | Evaluator |
| `justification` | text | optional | Overall justification of the rating |
| `context` | text | optional | Context of the rating (annual review, incident, change, etc.) |
| `created_at` | datetime | auto | Creation date |

# RiskSource

`risks.models.ebios.risk_source.RiskSource`

Risk source (SR): an element (individual, group, organization, State, phenomenon) at the origin of the risk. Reference prefix: `ERSC`.

## 4.2.1 Entity: RiskSource (Risk source)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix ERSC | Code (e.g. ERSC-1) |
| `name` | string | required, max 255 | Name of the SR |
| `description` | text | optional | Description |
| `category` | enum | required | `state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `service_provider`, `amateur`, `natural`, `other` |
| `motivation_level` | integer | optional, 1 to 4 | Motivation level : `1 - Low`, `2 - Moderate`, `3 - High`, `4 - Very high`. Empty reads *Not assessed* |
| `motivation_description` | text | optional | Qualitative description |
| `resources_level` | integer | optional, 1 to 4 | Resources level : `1 - Limited`, `2 - Moderate`, `3 - Significant`, `4 - Unlimited` |
| `activity_level` | integer | optional, 1 to 4 | Observed activity level : `1 - Low` to `4 - Very high`. From 3, the threat level goes up by one |
| `threat_level` | integer | computed, 1 to 4 (V1-V4) | ANSSI threat level (grid A, [see README §2.8](README.md#28-anssi-scoring-grids)) |
| `is_retained` | boolean | required, default true | SR retained for the analysis |
| `retention_justification` | text | optional | Justification |
| `is_from_catalog` | boolean | required, default false | Sourced from the predefined ANSSI catalog |
| `criteria_snapshot` | json | computed | Snapshot of the scoring grid |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> `threat_level` is computed in `save()` according to grid A ([see README §2.8](README.md#28-anssi-scoring-grids)). The result is stored for use in filtering/indexing. The grid is configurable via a JSON field on [`RiskCriteria`](../risk-criteria.md) (key `ebios_threat_grid`).

## Creation and edition

A risk source is a row of the page of workshop 2 (see [README, 8.5](README.md)).

- **Creation** asks for five fields on one screen : the name, the category and the three ratings. The category is a decision : the select opens on *Choose...*, `other` is not saved for the reader. A rating may wait : it reads *Not assessed*, and the threat level is computed once the motivation and the resources are given. The study is known from the address (an EBIOS RM one, or the address is unknown) and is never asked.
- **The three ratings** are picked by the name of their level (`risks.constants.MotivationLevel`, `ResourcesLevel`, `ActivityLevel`), on the form, in the REST API and in the descriptions of the MCP tools. They were choices of bare numbers.
- **Edition** shows the source whole on one screen : its description, the description of its motivation, and whether it is retained, with the reason.
- **Deletion** is offered while the lifecycle step of the source is deletable.


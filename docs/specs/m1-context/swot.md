# SwotAnalysis

`context.models.swot.SwotAnalysis`

Represents a SWOT analysis carried out for a given scope.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Analysis title |
| `description` | text | optional | Analysis context |
| `analysis_date` | date | required | Date carried out |
| `workflow_state` | enum | required, default `draft` | Unified lifecycle: `draft`, `pending`, `validated`, `archived`. See [governance/workflow.md](../governance/workflow.md). |
| `validated_by` | relation | FK → User | Validator |
| `validated_at` | datetime | optional | Validation date |
| `items` | relation | O2M → SwotItem | SWOT items |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## SwotItem

Sub-entity: SWOT item.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `swot_analysis_id` | relation | FK → SwotAnalysis, required | Parent analysis |
| `quadrant` | enum | required | `strength`, `weakness`, `opportunity`, `threat` |
| `description` | text | required | Item description |
| `impact_level` | enum | required | `low`, `medium`, `high` |
| `related_issues` | relation | M2M → Issue | Associated issues |
| `related_objectives` | relation | M2M → Objective | Associated objectives |
| `order` | integer | required | Display order within the quadrant |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A SWOT analysis follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then worked
on its page.

**Creation** asks for the name, the analysis date, the description and the
scopes (not asked with a single scope). An analysis is the work of a team :
nobody answers for it by creating it, the form has no owner. The user lands on
the page of the new analysis, where its four boxes are filled.

**The page** lists what would make the record useful, shows the card of its
identity (name, analysis date, next review, description, scopes, tags) with
its *Edit*, then the four boxes and the strategies, worked on the page itself
as before.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Note something in each of its four boxes | It has an item in each quadrant | no |
| Plan when to do it again | `review_date` is set | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_swot_analysis` tool as
well.

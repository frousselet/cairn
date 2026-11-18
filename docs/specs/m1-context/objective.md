# Objective

`context.models.objective.Objective`

Represents an information security or compliance objective.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `reference` | string | required, unique | Reference code (e.g. OBJ-001) |
| `name` | string | required, max 255 | Objective title |
| `description` | text | optional | Detailed description |
| `category` | enum | required | `confidentiality`, `integrity`, `availability`, `compliance`, `operational`, `strategic` |
| `type` | enum | required | `security`, `compliance`, `business`, `other` |
| `target_value` | string | optional | Measurable target value |
| `current_value` | string | optional | Current value |
| `unit` | string | optional | Unit of measurement |
| `measurement_method` | rich text | optional | Measurement method. Typed in the rich-text editor, stored as submitted and sanitised when shown (`\|rich`) |
| `measurement_frequency` | enum | optional | `monthly`, `quarterly`, `semi_annual`, `annual` |
| `target_date` | date | optional | Target achievement date |
| `owner_id` | relation | FK → User, required | Objective owner |
| `status` | enum | required | `draft`, `active`, `achieved`, `not_achieved`, `cancelled` |
| `progress_percentage` | integer | optional, 0-100 | Progress percentage |
| `related_issues` | relation | M2M → Issue | Issues addressed |
| `related_stakeholders` | relation | M2M → Stakeholder | Stakeholders concerned |
| `parent_objective_id` | relation | FK → Objective, optional | Parent objective (hierarchy) |
| `controls` | relation | reverse M2M ← [Control](../m8-controls/control.md) `objectives` | Controls contributing to the objective |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

An objective follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then
completed on its page.

**Creation** asks for the title, the category, the type, the owner (whoever
creates it, unless they say otherwise), the target date and the scopes (not
asked with a single scope). The user lands on the page of the new objective.

**Opened from an issue** (`/context/objectives/create/?issue=<id>`, the *New
objective* button of the *Relations* card of an issue), the objective answers
that issue : the link is carried by the form and not asked. The issue is looked
up within the user's scopes, and carried only when its lifecycle makes it
linkable : a draft issue has no such button and says why.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (title, category,
type, owner, description, scopes, tags), measurement (target value, unit,
method, frequency), progress and dates (current value, progress, target date,
next review, status) and relations (the issues it answers, the stakeholders
that expect it, its parent objective; its sub-objectives are listed). Status
and progress sit in the same card, where RS-02 is said : marking an objective
achieved asks for a progress of 100.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Say which figure tells whether it is reached | `target_value` is set | no |
| Give it a date | `target_date` is set | no |
| Link the issues it answers | `related_issues` holds an issue | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_objective` tool as well.

**Relations.** `related_issues`, `related_stakeholders` and `parent_objective`
were set over the REST API, the MCP server and the administration only : the
form had no field for them and the page did not show them. A picker offers
what its lifecycle makes linkable, plus what the objective already holds
(`linkable_or_linked`), within the user's scopes; an objective is not offered
as its own parent. The pages of an issue and of a stakeholder list the
objectives linked to them, and the three pages name a linked record only to a
reader whose scopes reach it.

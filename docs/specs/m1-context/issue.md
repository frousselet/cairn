# Issue

`context.models.issue.Issue`

Represents an internal or external issue that may influence the organization's ability to achieve the intended outcomes of its GRC framework.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Issue title |
| `description` | text | optional | Detailed description |
| `type` | enum | required | `internal`, `external` |
| `category` | enum | required | See list below |
| `impact_level` | enum | required | `low`, `medium`, `high`, `critical` |
| `trend` | enum | optional | `improving`, `stable`, `degrading` |
| `source` | string | optional | Source of the issue identification |
| `related_stakeholders` | relation | M2M → Stakeholder | Linked stakeholders |
| `review_date` | date | optional | Next review date |
| `status` | enum | required | `identified`, `active`, `monitored`, `closed` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Issue categories (`category` values):**

- *Internal issues:* `strategic`, `organizational`, `human_resources`, `technical`, `financial`, `cultural`
- *External issues:* `political`, `economic`, `social`, `technological`, `legal`, `environmental`, `competitive`, `regulatory`

> Note: Categories must be configurable by the administrator (add/edit/delete).

## Creation, completion, completeness

An issue follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed on its
page.

**Creation** asks for the title, the category, the impact level, the
description and the scopes (not asked with a single scope). The impact level
is a decision : the form opens on no answer and requires one (rule F8). An
issue is a fact of the context : nobody answers for it, the form has no owner.
The user lands on the page of the new issue.

**The type is not asked**, at creation or afterwards. A category is internal
or external, never both (RS-01) : the form offers the categories under
*Internal* and *External* and reads the type from the one picked, so the pair
the model refuses cannot be composed. The REST API and the MCP server still
take both fields, and the model still checks them against each other.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (title, category,
source, description, scopes, tags) and impact and follow-up (impact level,
trend, next review, status).

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Say why it matters for security | `description` holds a text | no |
| Plan its next review | `review_date` is set | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_issue` tool as well.

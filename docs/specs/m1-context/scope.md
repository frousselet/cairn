# Scope

`context.models.scope.Scope`

Represents the scope covered by the GRC framework.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `name` | string | required, max 255 | Scope name |
| `description` | text | required | Detailed description of the scope |
| `version` | string | required | Version of the scope document |
| `workflow_state` | enum | required, default `draft` | Standardised perimeter lifecycle: `draft` → `definition` → `validation` → `in_force` → `review` (periodic, looping back to `in_force`), with `archived` as the from-any exit (and restore to `draft`). `in_force` and `review` count in reports and are linkable; only `draft` is deletable. Runs the [standardised lifecycle engine](../governance/lifecycle.md) (`Scope.LIFECYCLE_NAME = "scope"`), not the default workflow. |
| `boundaries` | text | optional | Scope boundaries and exclusions |
| `justification_exclusions` | text | optional | Justification of exclusions |
| `geographic_scope` | text | optional | Geographic scope |
| `organizational_scope` | text | optional | Organizational scope |
| `technical_scope` | text | optional | Technical scope |
| `applicable_standards` | relation | M2M → Referential | Applicable standards |
| `effective_date` | date | optional | Effective date. Filled in with the day the scope comes into force when it is empty; a date typed beforehand is kept (RS-09) |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A scope follows the [usability standard](../../sdk/usability-standard.md) :
it is created short, then completed on its page.

**Creation** asks for the icon, the name, the description and, once another
scope exists, the parent scope (chosen among the scopes the user is allowed).
Nothing else. The user lands on the page of the new scope. `?parent=<uuid>`
starts a sub-scope from its parent.

**The page** lists what the scope still needs (below) and shows one card per
section of its form, each with its own dialog : identity (name, icon, parent,
description, tags), coverage (geographic, organizational, technical),
boundaries and exclusions, sites, managers, dates.

**Completeness** (`Scope.COMPLETENESS`, rule RS-08) :

| Key | The scope... | Tested on | Holds the lifecycle |
|---|---|---|---|
| `boundaries` | says where it stops | `boundaries` is not empty | yes |
| `managers` | names at least one manager | `managers` has a row | yes |
| `coverage` | says what it covers | one of `geographic_scope`, `organizational_scope`, `technical_scope` | no (advised) |
| `sites` | lists the sites it covers | `included_sites` has a row | no (advised) |
| `review` | plans its next review | `review_date` is set | no (advised) |

The REST API serves it with a single scope
(`completeness : {complete, can_advance, missing : [{key, label, blocking}]}`)
and the MCP `get_scope` tool reports the same.

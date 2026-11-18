# Role

`context.models.role.Role`

Represents a role within the GRC framework.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Role title |
| `description` | text | optional | Role description |
| `type` | enum | required | `governance`, `operational`, `support`, `control` |
| `responsibilities` | relation | O2M → Responsibility | Associated responsibilities |
| `assigned_users` | relation | M2M → User | Assigned users |
| `is_mandatory` | boolean | required, default false | Mandatory role (required by a standard) |
| `source_standard` | string | optional | Source standard (e.g. "ISO 27001 - §5.3") |
| `status` | enum | required | `active`, `inactive` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

Responsibilities are managed directly from the role detail page:
adding, editing and deleting them through an HTMX drawer, with the section
refreshing without a full page reload. These actions are protected by the
`context.role.update` permission.

Any creation, modification or deletion of a responsibility **sends the role
back to its initial state (draft)**: the approval is reset, the version is
incremented and the demotion is recorded in the role's history, so that it can
be re-validated. This behavior applies both from the interface and through the
REST API (`Role.send_back_to_draft()`, single source). Roles in a terminal
state (archived / cancelled) are not affected.

The role's history **merges the history of its responsibilities** (each
responsibility has its own `HistoricalRecords` tracking): adding, modifying and
deleting a responsibility therefore appear on the role's timeline. A deletion
displays the values of the removed responsibility and carries a "Responsibility"
label.

## Responsibility

Sub-entity: responsibility associated with a role.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `role_id` | relation | FK → Role, required | Parent role |
| `description` | text | required | Responsibility description |
| `raci_type` | enum | required | `responsible`, `accountable`, `consulted`, `informed` |
| `related_activity_id` | relation | FK → Activity, optional | Associated activity |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A role follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed on its
page.

**Creation** asks for the title, the type, who holds it, the description and
the scopes (not asked with a single scope). A role is held, not owned :
whoever creates it is not put on it. The user lands on the page of the new
role.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (title, type, source
standard, description, mandatory, scopes, tags, status) and who holds it. Its
responsibilities are rows added, edited and removed from the page, as before.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Give it to a person | `assigned_users` holds a user | no |
| Say what it answers for | It has a responsibility | no |

Nothing holds its lifecycle back : a mandatory role nobody holds is flagged on
its page and on the dashboard (RS-06), as before. The REST API returns the
list in `completeness` on a single record, and the MCP `get_role` tool as
well.

**Who holds it.** The picker offers the active accounts, plus whoever already
holds the role : it offered the active accounts only, so that saving a role
silently removed a holder whose account had been deactivated. Taking someone
off a role is a decision, made by unpicking them.

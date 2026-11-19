# Stakeholder

`context.models.stakeholder.Stakeholder`

Represents any person or organization that can affect, be affected by, or perceive itself to be affected by a decision or activity.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Stakeholder name |
| `type` | enum | required | `internal`, `external` |
| `category` | enum | required | See list below |
| `description` | text | optional | Description |
| `contact_name` | string | optional | Primary contact name |
| `contact_email` | string | optional, email format | Contact email |
| `contact_phone` | string | optional | Contact phone |
| `influence_level` | enum | required | `low`, `medium`, `high` |
| `interest_level` | enum | required | `low`, `medium`, `high` |
| `expectations` | relation | O2M → StakeholderExpectation | Expectations and requirements |
| `related_issues` | relation | M2M → Issue | Associated issues |
| `status` | enum | required | `active`, `inactive` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Stakeholder categories (`category` values):**

`executive_management`, `employees`, `customers`, `suppliers`, `partners`, `regulators`, `shareholders`, `insurers`, `public`, `competitors`, `unions`, `auditors`, `other`

> Note: Categories must be configurable by the administrator.

## Creation, completion, completeness

A stakeholder follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed
on its page.

**Creation** asks for the name, the type, the category, the influence level,
the interest level and the scopes (not asked with a single scope). The two
levels are decisions : the form opens on no answer and requires one (rule F8).
A stakeholder is a fact of the context : nobody answers for it, the form has
no owner. The user lands on the page of the new stakeholder.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (name, type,
category, description, scopes, tags), contact, and influence and interest
(influence, interest, next review, status). Its expectations are rows added,
edited and removed from the page (below). A *Relations* card lists the issues
that concern it and the objectives linked to it, when there are any : both are
set from the issue or the objective.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Add an expectation | It has an expectation | no |
| Fill in a contact | `contact_name` or `contact_email` is set | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_stakeholder` tool as well.

## StakeholderExpectation

Sub-entity: expectation of a stakeholder.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `stakeholder_id` | relation | FK → Stakeholder, required | Parent stakeholder |
| `description` | rich text | required | Description of the expectation or requirement. Typed in the rich-text editor, stored as submitted and sanitised when shown (`\|rich`) |
| `type` | enum | required | `requirement`, `expectation`, `need` |
| `priority` | enum | required | `low`, `medium`, `high`, `critical` |
| `is_applicable` | boolean | required, default true | Applicable to the scope |
| `linked_requirements` | relation | M2M → Requirement | Linked compliance requirements (Compliance module) |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

### Recording an expectation

An expectation is a row of its stakeholder, added, edited and removed from the
page of the stakeholder, each on one screen (description, type, priority,
applicable). The interface used to list expectations without any way to write
one : they could only be created over the REST API or the MCP server.

| Action | URL | Permission |
| --- | --- | --- |
| Add | `/context/stakeholders/<stakeholder>/expectations/create/` | `context.expectation.create` |
| Edit | `/context/expectations/<id>/edit/` | `context.expectation.update` |
| Remove | `/context/expectations/<id>/delete/` | `context.expectation.delete` |

An expectation is filed under the scopes of its stakeholder
(`scope_parent_lookup = "stakeholder__scopes"`) : a stakeholder out of the
user's scopes, or an expectation of one, answers as an unknown record (`404`).

# Threat

`risks.models.threat.Threat`

An event that could happen and do harm : an attack, a mistake, a natural event.
Threats are kept in one shared catalogue, so that every risk analysis names the
same event the same way. A threat runs the default lifecycle (draft, pending
validation, validated, archived) and is linked into an analysis once validated.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `THRT-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | Scopes it is filed under |
| `name` | string | required, max 255 | What could happen |
| `description` | text | optional, HTML | How it would unfold |
| `type` | enum | required | `deliberate`, `accidental`, `environmental`, `other` |
| `origin` | enum | optional | `human_internal`, `human_external`, `natural`, `technical`, `other` |
| `category` | enum | optional | `ThreatCategory` (`malware`, `social_engineering`, `unauthorized_access`, ...) |
| `typical_likelihood` | integer | optional | How often it is expected, on the likelihood scale of the risk criteria. Shown, not computed with |
| `is_from_catalog` | boolean | default false | It comes from a reference catalogue rather than from an analysis |
| `status` | enum | default `active` | `active`, `inactive`. A filter of the register, beside the lifecycle |
| `tags` | relation | M2M -> Tag | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Creation, completion, completeness

A threat follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then completed on its
page.

**Creation** asks for the name, the type, the origin, the category, the
description and the scopes (not asked with a single scope). Nobody answers for
a catalogue entry : the form has no owner. The user lands on the page of the
new threat.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (name, type, origin,
category, description, scopes, tags), likelihood and status (typical
likelihood, from catalog, status).

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Fill in the description | `description` holds a text | no |

Nothing holds the lifecycle of a threat back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_threat` tool as well.

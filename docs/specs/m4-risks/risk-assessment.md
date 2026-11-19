# RiskAssessment

`risks.models.risk_assessment.RiskAssessment`

Risk assessment campaign conducted following one or the other methodology (ISO 27005 or EBIOS RM). Root entity that groups together all analysis elements.

## 2.1 Entity: RiskAssessment (Risk assessment)

Represents a risk assessment campaign, conducted following one or the other methodology. It is the root entity that groups together all analysis elements.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `reference` | string | required, unique | Reference code (e.g. RA-2026-001) |
| `name` | string | required, max 255 | Assessment title |
| `description` | text | optional | Description and context |
| `methodology` | enum | required | `iso27005`, `ebios_rm` |
| `assessment_date` | date | optional | Date carried out |
| `assessor_id` | relation | FK → User, optional | Whoever conducts the assessment. The creator by default |
| `risk_criteria_id` | relation | FK → RiskCriteria, optional | Applied risk criteria. The default criteria of the organisation are proposed at creation, and used to rate its risks when none is set |
| `status` | enum | required | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optional | Validator |
| `validated_at` | datetime | optional | Validation date |
| `next_review_date` | date | optional | Next review date |
| `summary` | text | optional | Summary of results |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Implementation note : the original specification made `assessment_date`,
> `assessor_id` and `risk_criteria_id` required and listed a `team_members`
> relation. The model keeps the three optional and has no team : an assessment
> is opened before its date is known, and the page lists what it still needs.

## Creation, completion, completeness

A risk assessment follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then
completed on its page.

**Creation** asks for the name, the methodology, the assessor (the creator by
default), the risk criteria, the description and the scopes (not asked with a
single scope). The methodology is a decision : the model answers `iso27005` by
default, the form opens on no answer and requires one (rule F8), since the
method decides the screens the assessment uses. The criteria the organisation
marked as its default are proposed : that default is a decision somebody took.
The user lands on the page of the new assessment.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (name, methodology,
assessor, criteria, description, scopes, tags), dates and summary (assessment
date, next review, summary).

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Choose the risk criteria | `risk_criteria` is set | no |
| Assign an assessor | `assessor` is set | no |
| Set the next review date | `next_review_date` is set | no |

Nothing holds the lifecycle of an assessment back. The REST API returns the
list in `completeness` on a single record, and the MCP `get_risk_assessment`
tool as well.

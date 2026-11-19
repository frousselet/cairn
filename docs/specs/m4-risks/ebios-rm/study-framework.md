# StudyFramework

`risks.models.ebios.study_framework.StudyFramework`

Formalizes the prerequisites required by ANSSI before workshop 1: participants, frameworks, assumptions, constraints. Reference prefix: `EFRA`.

## 4.0.1 Entity: StudyFramework (Study framework)

Formalizes the prerequisites required by ANSSI before workshop 1: participants, frameworks, assumptions, constraints.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required, unique | Parent assessment (1 framework per assessment) |
| `reference` | string | required, unique, prefix EFRA | Code (e.g. EFRA-1) |
| `mission_statement` | text | asked before workshop 0 is validated | Description of the mission under study |
| `business_perimeter` | text | asked before workshop 0 is validated | Business perimeter (activities, processes) |
| `technical_perimeter` | text | asked before workshop 0 is validated | Technical perimeter (support assets, infrastructures) |
| `temporal_perimeter` | text | asked before workshop 0 is validated | Time horizon (study start / end date) |
| `financial_envelope` | decimal | optional | Allocated budget envelope |
| `participants` | M2M -> User | optional | Study participants |
| `participants_external` | json | optional, validated | List of external participants : `{name, role, organization}` entries (see External participants) |
| `applicable_frameworks` | M2M -> Framework | optional | Applicable frameworks (ISO 27001, NIS2, GDPR, etc.) |
| `assumptions` | text | optional | Assumptions retained |
| `constraints` | text | optional | Constraints (organizational, technical, legal) |
| `expected_deliverables` | text | optional | Expected deliverables |
| `status` | enum | required | `draft`, `validated` |
| `created_by`, `created_at`, `updated_at` | - | auto | `BaseModel` standard |

## Edition

The study framework is created empty with its assessment (it has no creation form) and edited from the page of workshop 0, one card at a time (see [README, 8.3](README.md)). Its form has four sections :

| Section | Fields | Card of the page |
|---|---|---|
| `mission` | `mission_statement` | Mission statement |
| `perimeters` | `business_perimeter`, `technical_perimeter`, `temporal_perimeter` | Perimeters of the study |
| `participants` | `participants`, `participants_external`, `applicable_frameworks` | Participants and applicable frameworks |
| `conditions` | `assumptions`, `constraints`, `expected_deliverables`, `financial_envelope` | Assumptions, constraints and expected deliverables |

- The seven texts are typed in the editor and shown formatted (they were printed with their tags).
- The internal participants are picked among the active accounts; whoever already takes part stays once their account is closed.
- The applicable frameworks are picked among the validated ones; a framework the study already names stays.
- `participant_ids`, `applicable_framework_ids` and `participants_external` set the same through the MCP tools.

What the study framework must hold before workshop 0 is validated is declared on the progress of the workshop : see [EbiosWorkshopProgress, Completeness](workshop-progress.md#completeness).

## External participants

`participants_external` is a list of entries `{"name", "role", "organization"}` : the people from outside the organisation who take part in the study (a consultant who runs the workshops, a supplier).

- **Shape**, held by a validator of the field on every surface that writes it (the form of workshop 0, the REST API, the MCP tool) : a list of 50 entries at most, each an object with no other key than these three, each value a text of 150 characters at most, the name filled in. Anything else is refused (`400` on the REST API, an error of the MCP tool).
- **On the page of workshop 0** they are typed as text, one person per line : `name, role, organisation`. What follows the second comma is the organisation, commas included. A part that holds a comma is typed between quotation marks, the way a spreadsheet writes it (`"Renard, Claire", facilitator`), and is shown that way when the form is opened again, so that what is shown reads back as it was.
- **Saving the card without touching them leaves the list as it is** : a list set through the API is rewritten only when the text says something else.
- **Reading is lenient** : a row written before the shape was held is read for what it has (an entry without a name is left out), and the page never fails on it. The MCP tool validates the whole record on each write : it refuses to update a study framework whose stored list has another shape until the call sends a valid one.


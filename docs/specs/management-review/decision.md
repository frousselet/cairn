# ManagementReviewDecision

`reports.models.management_review.ManagementReviewDecision`

Structured decision output required by ISO 27001:2022 clause 9.3.3, feeding the review minutes and seeding downstream action plans.

Structured capture of the decisions required by clause 9.3.3. Used to produce the "Decisions" block of the minutes and to automatically seed action plans.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (prefix `DECS`), unique | e.g. `DECS-1` |
| `review` | FK → ManagementReview | required, CASCADE | Originating review |
| `category` | enum | required | `improvement`, `isms_change`, `resource_allocation`, `risk_acceptance`, `objective_adjustment`, `policy_update`, `other` |
| `input_clause` | enum | optional | The 9.3.2 input the decision relates to (`a`–`g`) |
| `title` | string | required, max 255 | Short title |
| `description` | text | required | Full text of the decision |
| `rationale` | text | optional | Justification, contextual elements |
| `owner` | FK → User | required | Person responsible for implementation |
| `due_date` | date | required | Due date |
| `priority` | enum | required | `low`, `medium`, `high`, `critical` |
| `status` | enum | required | `pending`, `in_progress`, `implemented`, `cancelled` |
| `implemented_at` | date | optional | Actual implementation date |
| `implementation_evidence` | text | optional | Evidence (link to a document, URL) |
| `linked_action_plan` | FK → ComplianceActionPlan | optional, SET_NULL | Action plan generated from this decision |
| `linked_treatment_plan` | FK → RiskTreatmentPlan | optional, SET_NULL | Treatment plan generated |
| `linked_objective` | FK → Objective | optional, SET_NULL | ISMS objective created/adjusted |
| `linked_isms_change` | FK → IsmsChange | optional, SET_NULL | Associated ISMS change |
| `created_at`, `updated_at` | datetime | auto | |

**History** : `HistoricalRecords`.

**Business rules** :

- A review can only move to `closed` if **all of its decisions** have `owner` AND `due_date` filled in.
- When a decision moves to `implemented`, if `linked_action_plan` is set, its status must be `CLOSED` or `VALIDATED` (business safeguard, non-blocking UI warning).
- A "Create an action plan from this decision" action generates a pre-filled `ComplianceActionPlan` and sets `linked_action_plan` + `originating_review` (cf. [README.md](README.md#changes-to-existing-models)).

**Interface** ([usability standard](../../sdk/usability-standard.md)) :

- A decision is recorded from the *Decisions* card of its review, in the drawer, on one screen : the title, the category and the priority (decisions : each select opens on *Choose...*, where *medium* was saved for whoever did not choose), the description, the owner (whoever records it, unless they name someone else) and the due date. The review comes from the address and is never a question. It opens on its page.
- The edit form has four sections, one per card of the page : `decision` (category, input clause, title, description, priority), `follow_up` (owner, due date, status), `rationale` and `implementation` (date and evidence). The long texts are shown formatted, sanitized at render time (`|rich`); a page help (`reports.decision_detail`) says what a decision is and what to do first.
- What the page lists under *To complete* (`ManagementReviewDecision.COMPLETENESS`, also `completeness` on `GET /api/v1/reports/decisions/{id}/` and the `get_management_review_decision` MCP tool) : the owner and the due date, which the closure of the review waits for; advised, the rationale and, once the decision is implemented, its implementation date and evidence. The decision runs no lifecycle : nothing is refused on its own record, the closure of its review is.

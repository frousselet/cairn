# RiskTreatmentPlan

`risks.models.treatment.RiskTreatmentPlan`

Treatment plan listing the actions associated with a risk.

## 2.6 Entity: RiskTreatmentPlan (Risk treatment plan)

Represents the treatment actions associated with a risk.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `risk_id` | relation | FK → Risk, required | Treated risk |
| `reference` | string | required, unique | Reference code (e.g. PTR-001) |
| `name` | string | required, max 255 | Plan title |
| `description` | text | optional | Detailed description |
| `treatment_type` | enum | required | `mitigate`, `transfer`, `avoid` |
| `actions` | relation | O2M → TreatmentAction | Treatment actions |
| `expected_residual_likelihood` | integer | optional | Expected residual likelihood |
| `expected_residual_impact` | integer | optional | Expected residual impact |
| `cost_estimate` | decimal | optional | Overall cost estimate |
| `owner_id` | relation | FK → User, required | Plan owner |
| `start_date` | date | optional | Start date |
| `target_date` | date | required | Target completion date |
| `completion_date` | date | optional | Actual completion date |
| `progress_percentage` | integer | optional, 0-100 | Overall progress |
| `status` | enum | required | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A treatment plan follows the [usability standard](../../sdk/usability-standard.md) : it is created short, then
completed on its page.

**Creation** asks for the risk, the name, the treatment type, the owner (the
creator by default), the target date and the description. Opened from the page
of a risk (*New plan*), the risk is not asked (rule F2) : that link used to
carry no risk, and the reader had to pick again the risk they came from. The
user lands on the page of the new plan.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : identity (name, risk, treatment
type, owner, description, tags), target and planning (expected residual
likelihood and impact, read on the scales of the criteria of the risk's
assessment, cost estimate, dates) and related action plans.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Set the level it aims to bring the risk to | Both expected residual values are set | no |
| Name who carries it | `owner` is set | no |
| Set the date it is due | `target_date` is set | no |
| List the actions it is made of | It has an action | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_risk_treatment_plan` tool
as well.

An **action** is a row of its plan, added from the page of the plan on one
screen : what is to be done, by whom and for when. It starts as planned and at
the end of the list; its status and its order are changed from its row.

The risk named in the address of a creation (`?risk=<id>`) is looked up within
the reader's scopes : none, a malformed one or one out of reach read the same,
and none raises.

## TreatmentAction

`risks.models.treatment.TreatmentAction`

### 2.7 Sub-entity: TreatmentAction (Treatment action)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `treatment_plan_id` | relation | FK → RiskTreatmentPlan, required | Parent treatment plan |
| `description` | rich text | required | Description of the action. Typed in the rich-text editor, stored as submitted and sanitised when shown (`\|rich`) |
| `owner_id` | relation | FK → User, required | Action owner |
| `target_date` | date | required | Target date |
| `completion_date` | date | optional | Completion date |
| `controls` | relation | reverse M2M ← [Control](../m8-controls/control.md) `treatment_plans` | Controls this plan creates or reinforces |
| `status` | enum | required | `planned`, `in_progress`, `completed`, `cancelled` |
| `order` | integer | required | Execution order |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

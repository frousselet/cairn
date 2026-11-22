# RiskAcceptance

`risks.models.acceptance.RiskAcceptance`

Formalizes the acceptance of a risk by its owner, in accordance with the organization's decision-making process.

## 2.8 Entity: RiskAcceptance (Risk acceptance)

Formalizes the acceptance of a risk by the risk owner, in accordance with the organization's decision-making process.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `risk_id` | relation | FK → Risk, required | Accepted risk |
| `accepted_by` | relation | FK → User, required | Accepting party (risk owner) |
| `accepted_at` | datetime | required | Acceptance date |
| `risk_level_at_acceptance` | integer | required | Risk level at the time of acceptance |
| `justification` | text | required | Justification for the acceptance |
| `conditions` | text | optional | Acceptance conditions (e.g. quarterly review) |
| `valid_until` | date | optional | Validity date of the acceptance |
| `review_date` | date | required | Mandatory review date |
| `status` | enum | required | `active`, `expired`, `revoked`, `renewed` |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A risk acceptance follows the [usability standard](../../sdk/usability-standard.md) : it is created on one screen,
then completed on its page.

**Creation** asks for the risk, the justification, the conditions and the two
dates (valid until, review date). Opened with a risk in its address
(`?risk=<id>`), the risk is not asked (rule F2). Nobody answers for an
acceptance by filing it : who accepted, when and at which level is recorded
when the acceptance becomes active (RV-05). The user lands on the page of the
new acceptance.

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : acceptance (risk,
justification, conditions, tags) and validity (valid until, review date). What
the lifecycle recorded (accepted by, level at acceptance, acceptance date) is
shown in a card that is not edited.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Set the end of validity | `valid_until` is set | no |
| Set the review date | `review_date` is set | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_risk_acceptance` tool as
well.

**Who accepts the risk.** `draft → active` accepts the risk : it asks for
`risks.acceptance.approve` (held by the RSSI / DPO and the administrators, not
by a contributor), on the lifecycle bar, the generic transition endpoint, the
MCP transition tool and a status an MCP tool writes directly. Who drafts the
acceptance does not accept the risk alone. The other moves (expire, renew,
revoke) ask for `risks.acceptance.update`.

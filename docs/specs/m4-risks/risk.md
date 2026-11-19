# Risk

`risks.models.risk.Risk`

Identified risk, regardless of the originating methodology. Central entity of the risk register.

## 2.5 Entity: Risk (Risk)

Represents an identified risk, regardless of the originating methodology. It is the central entity of the risk register.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `assessment_id` | relation | FK → RiskAssessment, required | Source assessment |
| `reference` | string | required, unique | Reference code (e.g. RSK-001) |
| `name` | string | required, max 255 | Risk title |
| `description` | text | required | Narrative description of the risk scenario |
| `risk_source` | enum | required | `iso27005_analysis`, `ebios_strategic_scenario`, `ebios_operational_scenario`, `incident`, `audit`, `compliance`, `manual` |
| `source_entity_id` | UUID | optional | Identifier of the source entity (ISO27005Risk, StrategicScenario, etc.) |
| `source_entity_type` | string | optional | Type of the source entity |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Impacted essential assets |
| `affected_support_assets` | relation | M2M → SupportAsset | Support assets concerned |
| `impact_confidentiality` | boolean | required, default false | Impact on confidentiality |
| `impact_integrity` | boolean | required, default false | Impact on integrity |
| `impact_availability` | boolean | required, default false | Impact on availability |
| `initial_likelihood` | integer | required | Initial (gross) likelihood: value on the scale |
| `initial_impact` | integer | required | Initial (gross) impact: value on the scale |
| `initial_risk_level` | integer | computed | Initial risk level (via the matrix) |
| `current_likelihood` | integer | optional | Current likelihood (after existing measures) |
| `current_impact` | integer | optional | Current impact |
| `current_risk_level` | integer | computed | Current risk level |
| `residual_likelihood` | integer | optional | Residual likelihood (after planned treatment) |
| `residual_impact` | integer | optional | Residual impact |
| `residual_risk_level` | integer | computed | Residual risk level |
| `treatment_decision` | enum | optional | `accept`, `mitigate`, `transfer`, `avoid`, `not_decided` |
| `treatment_justification` | text | optional | Justification for the treatment decision |
| `risk_owner_id` | relation | FK → User, required | Risk owner (decision-maker) |
| `controls` | relation | reverse M2M ← [Control](../m8-controls/control.md) `risks` | Controls treating this risk, with their effectiveness (RG-CTL-20) |
| `linked_requirements` | relation | M2M → Requirement | Associated compliance requirements |
| `linked_incidents` | relation | M2M → Incident | Linked incidents |
| `priority` | enum | optional | `low`, `medium`, `high`, `critical` |
| `status` | enum | required | `identified`, `analyzed`, `evaluated`, `treatment_planned`, `treatment_in_progress`, `treated`, `accepted`, `closed`, `monitoring` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Creation, completion, completeness

A risk follows the [usability standard](../../sdk/usability-standard.md), with one particularity : it has no register
dialog. A risk comes out of an assessment (the consolidation of ISO 27005
analyses, an EBIOS RM workshop, or the assessment page for a risk noted by
hand), and the creation view sends a request with no assessment to the list of
assessments.

**Creation**, opened from an assessment, asks for the name, the source, the
owner, the essential assets it would harm and the description. The assessment
is the one the form was opened from : it is not asked (rule F2). The owner is
asked and never assumed : whoever notes a risk is seldom the one entitled to
accept it. The user lands on the page of the new risk.

**The page** lists what would make the record useful, then shows a card per
section of its form, each with its own *Edit* : identity (name, assessment and
source, both set once, owner, description, security needs affected, tags),
evaluation (initial and current likelihood and impact, read on the scales of
the assessment's criteria), treatment (decision, priority, justification,
review date) and relations (essential and support assets, requirements).

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Rate the current likelihood and impact | `current_likelihood` and `current_impact` are set | no |
| Assign a risk owner | `risk_owner` is set | no |
| Choose a treatment decision | `treatment_decision` is not `not_decided` | no |
| Link the affected assets | It has an essential or a support asset | no |

Nothing holds the lifecycle of a risk back : none of these was required
before, and the standard invents no governance. The REST API returns the list
in `completeness` on a single record, and the MCP `get_risk` tool as well.

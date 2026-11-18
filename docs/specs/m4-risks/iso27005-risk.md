# ISO27005Risk

`risks.models.iso27005_risk.ISO27005Risk`

Detailed analysis of a risk scenario following the ISO 27005 methodology: a triplet (threat, vulnerability, asset) with likelihood and impact assessment.

## 3.3 Entity: ISO27005Risk (ISO 27005 risk analysis)

Represents the detailed analysis of a risk scenario following the ISO 27005 methodology: a triplet (threat, vulnerability, asset) with likelihood and impact assessment.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `assessment_id` | relation | FK → RiskAssessment, required | Parent assessment (methodology = iso27005) |
| `threat_id` | relation | FK → Threat, required | Exploiting threat |
| `vulnerability_id` | relation | FK → Vulnerability, required | Exploited vulnerability |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Impacted essential assets |
| `affected_support_assets` | relation | M2M → SupportAsset | Targeted support assets |
| `threat_likelihood` | integer | required | Threat likelihood (on the scale) |
| `vulnerability_exposure` | integer | required | Vulnerability exposure level (on the scale) |
| `combined_likelihood` | integer | computed | Combined likelihood |
| `impact_confidentiality` | integer | optional | Impact on confidentiality (on the scale) |
| `impact_integrity` | integer | optional | Impact on integrity |
| `impact_availability` | integer | optional | Impact on availability |
| `max_impact` | integer | computed | Maximum impact retained |
| `risk_level` | integer | computed | Risk level (via matrix) |
| `existing_controls` | text | optional | Existing controls taken into account |
| `existing_measures` | relation | M2M → Measure | Formalized existing measures |
| `risk_id` | relation | FK → [Risk](risk.md), optional | Risk consolidated in the register |
| `description` | text | optional | Narrative description of the scenario |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Note: The ISO 27005 sub-module also includes the entities `Threat` (`risks.models.threat.Threat`) and `Vulnerability` (`risks.models.vulnerability.Vulnerability`), which are the reference catalogs for, respectively, the threats and the vulnerabilities used in the triplets.

## Creation, completion, completeness

An analysis follows the [usability standard](../../sdk/usability-standard.md) : it is opened short, then rated on its
page.

**Creation** asks for the threat, the vulnerability, the essential assets the
scenario would harm and its description. Opened from the page of an
assessment (*New analysis*), the assessment is not asked (rule F2); from the
register it is, among the assessments conducted with ISO 27005. Nobody owns a
scenario : the risk it is consolidated into has an owner. The user lands on
the page of the new analysis, where it is rated (the form used to return to
the assessment).

**The page** lists what would make the record useful, then shows one card per
section of its form, each with its own *Edit* : scenario (assessment, threat,
vulnerability, description, tags), evaluation (the five ratings and the
existing controls) and affected assets.

The five ratings (`threat_likelihood`, `vulnerability_exposure`, the three
impacts) are picked on the named levels of the criteria of the assessment,
where a bare number was typed against a helper that said *0-4* whatever the
scales were. A level stored on scales that have changed since is kept as it
is. A value off the scale is refused by the form.

| Requirement | Met when | Blocking |
| --- | --- | --- |
| Rate how likely and how severe it is | It has a combined likelihood and a maximum impact | no |
| Say what it would harm | It has an essential or a support asset | no |

Nothing holds its lifecycle back. The REST API returns the list in
`completeness` on a single record, and the MCP `get_iso27005_risk` tool as
well.

The assessment named in the address of a creation (`?assessment=<id>`) is
looked up within the reader's scopes : none, a malformed one or one out of
reach read the same, and none raises.

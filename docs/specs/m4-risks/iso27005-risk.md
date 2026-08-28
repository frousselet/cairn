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

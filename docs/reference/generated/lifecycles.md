<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from `core/lifecycle.py` and each app's `lifecycles.py` by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Lifecycles

Every domain record runs a registered lifecycle. A lifecycle is an ordered set of **steps** plus the **transitions** between them; the step carries the governance metadata the rest of the platform reads instead of hardcoding a status value.

| Flag | Read by |
| --- | --- |
| `counts_in_reports` | `reportable()` : dashboards, KPIs, reports |
| `linkable` | `linkable()` : the object pickers of other forms |
| `deletable` | `deletable_states()` : whether deletion is offered at all |

The engine is specified in [governance/lifecycle.md](../../specs/governance/lifecycle.md); the governance contract is in [governance/workflow.md](../../specs/governance/workflow.md).

**30 lifecycles** are declared in code. An administrator can override any of them from `/config/lifecycles/`; this page documents the shipped defaults.

## Summary

| Lifecycle | Steps | Transitions | Layout | Models |
| --- | --- | --- | --- | --- |
| [`action_plan`](#action-plan) | 10 | 17 | graph | `compliance.ComplianceActionPlan` |
| [`certificate`](#certificate) | 7 | 7 | graph | `assets.Certificate` |
| [`compliance_assessment`](#compliance-assessment) | 7 | 8 | graph | `compliance.ComplianceAssessment` |
| [`contract`](#contract) | 7 | 7 | graph | `assets.Contract` |
| [`default`](#default) | 4 | 4 | graph | `assets.AssetGroup`, `compliance.Finding`, `compliance.Framework`, `compliance.Requirement`, `context.Activity`, `context.Indicator`, `context.Issue`, `context.Objective`, `context.Role`, `context.Stakeholder`, `context.StakeholderFeedback`, `context.SwotAnalysis`, `incidents.IncidentResponsePlan`, `incidents.ReportingAuthority`, `incidents.ReportingObligationTemplate`, `risks.AttackPathStep`, `risks.AttackTechnique`, `risks.EcosystemStakeholder`, `risks.FearedEvent`, `risks.ISO27005Risk`, `risks.OperationalScenario`, `risks.RiskCriteria`, `risks.RiskSource`, `risks.RiskSourceObjectivePair`, `risks.StrategicScenario`, `risks.TargetedObjective`, `risks.Threat` |
| [`ebios_baseline_gap`](#ebios-baseline-gap) | 6 | 7 | graph | `risks.BaselineGap` |
| [`ebios_pacs_measure`](#ebios-pacs-measure) | 7 | 12 | graph | `risks.PACSMeasure` |
| [`ebios_security_baseline`](#ebios-security-baseline) | 4 | 4 | graph | `risks.SecurityBaseline` |
| [`ebios_study_framework`](#ebios-study-framework) | 3 | 3 | graph | `risks.StudyFramework` |
| [`ebios_summary`](#ebios-summary) | 5 | 6 | graph | `risks.EbiosSummary` |
| [`ebios_workshop`](#ebios-workshop) | 7 | 8 | graph | `risks.EbiosWorkshopProgress` |
| [`essential_asset`](#essential-asset) | 6 | 9 | graph | `assets.EssentialAsset` |
| [`incident`](#incident) | 11 | 16 | graph | `incidents.Incident` |
| [`incident_evidence`](#incident-evidence) | 8 | 9 | graph | `incidents.IncidentEvidence` |
| [`incident_notification`](#incident-notification) | 8 | 9 | graph | `incidents.IncidentNotification` |
| [`management_review`](#management-review) | 7 | 9 | graph | `reports.ManagementReview` |
| [`personal_data_breach`](#personal-data-breach) | 6 | 9 | graph | `incidents.PersonalDataBreach` |
| [`post_incident_review`](#post-incident-review) | 8 | 10 | graph | `incidents.PostIncidentReview` |
| [`risk`](#risk) | 11 | 16 | graph | `risks.Risk` |
| [`risk_acceptance`](#risk-acceptance) | 6 | 10 | graph | `risks.RiskAcceptance` |
| [`risk_assessment`](#risk-assessment) | 5 | 5 | graph | `risks.RiskAssessment` |
| [`risk_treatment_plan`](#risk-treatment-plan) | 7 | 12 | graph | `risks.RiskTreatmentPlan` |
| [`scope`](#scope) | 6 | 7 | graph | `context.Scope` |
| [`security_event`](#security-event) | 7 | 8 | graph | `incidents.SecurityEvent` |
| [`site`](#site) | 6 | 7 | graph | `context.Site` |
| [`supplier`](#supplier) | 8 | 10 | cycle | `assets.Supplier` |
| [`support_asset`](#support-asset) | 8 | 10 | graph | `assets.SupportAsset` |
| [`trust_center_document_request`](#trust-center-document-request) | 5 | 6 | graph | `trust_center.DocumentRequest` |
| [`trust_center_publication`](#trust-center-publication) | 4 | 6 | graph | `trust_center.TrustCenterCertification`, `trust_center.TrustCenterDocument`, `trust_center.TrustCenterMeasure`, `trust_center.TrustCenterSubprocessor` |
| [`vulnerability`](#vulnerability) | 7 | 9 | graph | `risks.Vulnerability` |

## action_plan

Run by `compliance.ComplianceActionPlan`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `new` | New | intermediate | - | - | yes |
| `to_define` | To define | intermediate | - | - | yes |
| `to_validate` | To validate | intermediate | yes | - | - |
| `to_implement` | To implement | intermediate | yes | yes | - |
| `implementation_to_validate` | Implementation to validate | intermediate | yes | yes | - |
| `validated` | Validated | intermediate | yes | yes | - |
| `closed` | Closed | archived | yes | - | - |
| `cancelled` | Cancelled | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `new` | Start | - | - | - |
| `new` | `to_define` | To define | - | - | - |
| `to_define` | `to_validate` | To validate | - | - | - |
| `to_validate` | `to_implement` | To implement | - | - | - |
| `to_validate` | `to_define` | To define | yes | - | - |
| `to_implement` | `implementation_to_validate` | Implementation to validate | - | - | - |
| `implementation_to_validate` | `validated` | Validated | - | - | - |
| `implementation_to_validate` | `to_implement` | To implement | yes | - | - |
| `validated` | `closed` | Closed | - | - | - |
| `new` | `cancelled` | Cancelled | - | - | - |
| `to_define` | `cancelled` | Cancelled | - | - | - |
| `to_validate` | `cancelled` | Cancelled | - | - | - |
| `to_implement` | `cancelled` | Cancelled | - | - | - |
| `implementation_to_validate` | `cancelled` | Cancelled | - | - | - |
| `validated` | `cancelled` | Cancelled | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## certificate

Run by `assets.Certificate`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `assessment` | Assessment | intermediate | yes | - | - |
| `certified` | Certified | intermediate | yes | yes | - |
| `under_renewal` | Under renewal | intermediate | yes | yes | - |
| `suspended` | Suspended | intermediate | yes | - | - |
| `expired` | Expired | intermediate | yes | - | - |
| `archived` | Archived | archived | yes | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `assessment` | Start assessment | - | - | - |
| `assessment` | `certified` | Certify | - | - | - |
| `certified` | `under_renewal` | Start renewal | - | - | - |
| `under_renewal` | `certified` | Renewed | - | - | - |
| `under_renewal` | `suspended` | Suspend | - | - | - |
| `under_renewal` | `expired` | Expire | - | - | - |
| any | `archived` | Archive | - | - | - |

## compliance_assessment

Run by `compliance.ComplianceAssessment`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Audit draft | draft | - | - | yes |
| `planned` | Planned | intermediate | yes | - | - |
| `in_progress` | In progress | intermediate | yes | - | - |
| `completed` | Completed | intermediate | yes | - | - |
| `closed` | Closed | archived | yes | - | - |
| `cancelled` | Cancelled | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `planned` | Planned | - | - | - |
| `draft` | `cancelled` | Cancelled | - | - | - |
| `planned` | `in_progress` | In progress | - | - | - |
| `planned` | `cancelled` | Cancelled | - | - | - |
| `in_progress` | `completed` | Completed | - | - | - |
| `completed` | `closed` | Closed | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## contract

Run by `assets.Contract`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `drafting` | Contract draft | intermediate | yes | - | - |
| `signing` | Under signature | intermediate | yes | - | - |
| `active` | In force | intermediate | yes | yes | - |
| `under_review` | Under review | intermediate | yes | yes | - |
| `expired` | Expired | intermediate | yes | - | - |
| `archived` | Archived | archived | yes | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `drafting` | Start drafting | - | - | - |
| `drafting` | `signing` | Send for signature | - | - | - |
| `signing` | `active` | Bring into force | - | - | - |
| `active` | `under_review` | Start review | - | - | - |
| `under_review` | `active` | Reviewed | - | - | - |
| `active` | `expired` | Expire | - | - | - |
| any | `archived` | Archive | - | - | - |

## default

Run by `assets.AssetGroup`, `compliance.Finding`, `compliance.Framework`, `compliance.Requirement`, `context.Activity`, `context.Indicator`, `context.Issue`, `context.Objective`, `context.Role`, `context.Stakeholder`, `context.StakeholderFeedback`, `context.SwotAnalysis`, `incidents.IncidentResponsePlan`, `incidents.ReportingAuthority`, `incidents.ReportingObligationTemplate`, `risks.AttackPathStep`, `risks.AttackTechnique`, `risks.EcosystemStakeholder`, `risks.FearedEvent`, `risks.ISO27005Risk`, `risks.OperationalScenario`, `risks.RiskCriteria`, `risks.RiskSource`, `risks.RiskSourceObjectivePair`, `risks.StrategicScenario`, `risks.TargetedObjective`, `risks.Threat`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `pending` | Pending validation | intermediate | - | - | - |
| `validated` | Validated | intermediate | yes | yes | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `pending` | Submit | - | `update` | - |
| `pending` | `draft` | Send back to draft | - | `update` | - |
| `pending` | `validated` | Validate | - | `approve` | - |
| `validated` | `archived` | Archive | - | `approve` | - |

## ebios_baseline_gap

Run by `risks.BaselineGap`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `identified` | Identified | intermediate | yes | - | yes |
| `accepted` | Accepted | intermediate | yes | - | - |
| `in_remediation` | In remediation | intermediate | yes | - | - |
| `remediated` | Remediated | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `identified` | Start | - | - | - |
| `identified` | `accepted` | Accepted | - | - | - |
| `identified` | `in_remediation` | In remediation | - | - | - |
| `accepted` | `in_remediation` | In remediation | - | - | - |
| `in_remediation` | `remediated` | Remediated | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## ebios_pacs_measure

Run by `risks.PACSMeasure`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `planned` | Planned | intermediate | yes | - | yes |
| `in_progress` | In progress | intermediate | yes | - | - |
| `completed` | Completed | archived | yes | - | - |
| `cancelled` | Cancelled | archived | - | - | - |
| `overdue` | Overdue | intermediate | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `planned` | Start | - | - | - |
| `planned` | `in_progress` | In progress | - | - | - |
| `in_progress` | `completed` | Completed | - | - | - |
| `planned` | `overdue` | Overdue | - | - | - |
| `in_progress` | `overdue` | Overdue | - | - | - |
| `overdue` | `in_progress` | In progress | - | - | - |
| `overdue` | `completed` | Completed | - | - | - |
| `planned` | `cancelled` | Cancelled | - | - | - |
| `in_progress` | `cancelled` | Cancelled | - | - | - |
| `overdue` | `cancelled` | Cancelled | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## ebios_security_baseline

Run by `risks.SecurityBaseline`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | yes | - | yes |
| `in_progress` | In progress | intermediate | yes | - | - |
| `completed` | Completed | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `in_progress` | In progress | - | - | - |
| `in_progress` | `completed` | Completed | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## ebios_study_framework

Run by `risks.StudyFramework`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | yes | - | yes |
| `validated` | Validated | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `validated` | Validated | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## ebios_summary

Run by `risks.EbiosSummary`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | yes | - | yes |
| `in_progress` | In progress | intermediate | yes | - | - |
| `under_review` | Under review | intermediate | yes | - | - |
| `validated` | Validated | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `in_progress` | In progress | - | - | - |
| `in_progress` | `under_review` | Under review | - | - | - |
| `under_review` | `validated` | Validated | - | - | - |
| `under_review` | `in_progress` | In progress | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## ebios_workshop

Run by `risks.EbiosWorkshopProgress`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `not_started` | Not started | intermediate | yes | - | yes |
| `in_progress` | In progress | intermediate | yes | - | - |
| `under_review` | Under review | intermediate | yes | - | - |
| `validated` | Validated | archived | yes | - | - |
| `rejected` | Rejected | intermediate | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `not_started` | Start | - | - | - |
| `not_started` | `in_progress` | In progress | - | - | - |
| `in_progress` | `under_review` | Under review | - | - | - |
| `under_review` | `validated` | Validated | - | - | - |
| `under_review` | `rejected` | Rejected | yes | - | - |
| `rejected` | `in_progress` | In progress | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## essential_asset

Run by `assets.EssentialAsset`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `identified` | Identified | intermediate | yes | yes | yes |
| `active` | Active | intermediate | yes | yes | - |
| `under_review` | Under review | intermediate | yes | yes | - |
| `decommissioned` | Decommissioned | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `identified` | Start | - | - | - |
| `identified` | `active` | Active | - | - | - |
| `identified` | `decommissioned` | Decommissioned | - | - | - |
| `active` | `under_review` | Under review | - | - | - |
| `under_review` | `active` | Active | - | - | - |
| `under_review` | `decommissioned` | Decommissioned | - | - | - |
| `active` | `decommissioned` | Decommissioned | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## incident

Run by `incidents.Incident`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `detected` | Detected | intermediate | yes | - | - |
| `triaged` | Triaged | intermediate | yes | yes | - |
| `investigating` | Investigating | intermediate | yes | yes | - |
| `contained` | Contained | intermediate | yes | yes | - |
| `eradicated` | Eradicated | intermediate | yes | yes | - |
| `recovered` | Recovered | intermediate | yes | yes | - |
| `post_incident_review` | Post-incident review | intermediate | yes | yes | - |
| `closed` | Incident closed | archived | yes | - | - |
| `reclassified` | Reclassified as event | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `detected` | Declare the incident | - | `create` | - |
| `detected` | `triaged` | Complete triage | - | `update` | - |
| `triaged` | `investigating` | Start investigation | - | `update` | - |
| `investigating` | `contained` | Record containment | - | `update` | - |
| `contained` | `eradicated` | Record eradication | - | `update` | - |
| `eradicated` | `recovered` | Record recovery | - | `update` | - |
| `recovered` | `post_incident_review` | Open the post-incident review | - | `update` | - |
| `post_incident_review` | `closed` | Close the incident | yes | `validate` | - |
| `recovered` | `investigating` | Reopen the investigation | yes | `update` | - |
| `closed` | `investigating` | Reopen a closed incident | yes | `validate` | - |
| `post_incident_review` | `investigating` | Send back to investigation | yes | `update` | - |
| `detected` | `reclassified` | Reclassify as an event | yes | `validate` | - |
| `triaged` | `reclassified` | Reclassify as an event | yes | `validate` | - |
| `investigating` | `reclassified` | Reclassify as an event | yes | `validate` | - |
| any | `archived` | Archive | yes | `validate` | - |
| `archived` | `draft` | Restore | - | `validate` | - |

## incident_evidence

Run by `incidents.IncidentEvidence`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft registration | draft | - | - | yes |
| `collected` | Collected | intermediate | yes | - | - |
| `secured` | Secured | intermediate | yes | yes | - |
| `analysed` | Analysed | intermediate | yes | yes | - |
| `retained` | Retained in custody | intermediate | yes | yes | - |
| `released` | Released | archived | yes | - | - |
| `destroyed` | Destroyed | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `collected` | Register the acquisition | - | `create` | - |
| `collected` | `secured` | Seal the evidence | - | `update` | - |
| `secured` | `analysed` | Record analysis | - | `update` | - |
| `secured` | `retained` | Move into retention | - | `update` | - |
| `analysed` | `retained` | Move into retention | - | `update` | - |
| `retained` | `released` | Release to a counterparty | yes | `approve` | - |
| `retained` | `destroyed` | Destroy the evidence | yes | `approve` | - |
| any | `archived` | Archive | yes | `approve` | - |
| `archived` | `draft` | Restore | - | `approve` | - |

## incident_notification

Run by `incidents.IncidentNotification`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `assessed` | To decide | intermediate | yes | - | yes |
| `required` | Notification required | intermediate | yes | - | - |
| `drafted` | Notification drafted | intermediate | yes | - | - |
| `sent` | Notification sent | intermediate | yes | - | - |
| `acknowledged` | Acknowledged by the recipient | intermediate | yes | - | - |
| `not_required` | Notification not required | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `assessed` | Register the obligation | - | `create` | - |
| `assessed` | `required` | Decide it is required | yes | `approve` | - |
| `assessed` | `not_required` | Decide it is not required | yes | `approve` | - |
| `required` | `drafted` | Draft the notification | - | `update` | - |
| `drafted` | `sent` | Record the filing | - | `update` | - |
| `sent` | `acknowledged` | Record the acknowledgement | - | `update` | - |
| `not_required` | `assessed` | Reopen the decision | yes | `approve` | - |
| any | `archived` | Archive | yes | `approve` | - |
| `archived` | `draft` | Restore | - | `approve` | - |

## management_review

Run by `reports.ManagementReview`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `planned` | Planned | intermediate | yes | - | yes |
| `in_preparation` | In preparation | intermediate | yes | - | - |
| `held` | Held | intermediate | yes | - | - |
| `closed` | Closed | archived | yes | - | - |
| `cancelled` | Cancelled | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `planned` | Start | - | - | - |
| `planned` | `in_preparation` | In preparation | - | - | - |
| `in_preparation` | `held` | Held | - | - | - |
| `held` | `closed` | Closed | - | - | - |
| `planned` | `cancelled` | Cancelled | yes | - | - |
| `in_preparation` | `cancelled` | Cancelled | yes | - | - |
| `held` | `cancelled` | Cancelled | yes | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## personal_data_breach

Run by `incidents.PersonalDataBreach`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `under_qualification` | Qualification in progress | intermediate | - | - | yes |
| `confirmed` | Confirmed breach | intermediate | yes | yes | - |
| `documented` | Documented under Art. 33(5) | intermediate | yes | yes | - |
| `not_a_breach` | Not a personal data breach | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `under_qualification` | Open the qualification | - | `create` | - |
| `under_qualification` | `confirmed` | Confirm the breach | yes | `approve` | - |
| `under_qualification` | `not_a_breach` | Rule out a breach | yes | `approve` | - |
| `confirmed` | `documented` | Complete the Art. 33(5) record | - | `approve` | - |
| `confirmed` | `under_qualification` | Reopen the qualification | yes | `approve` | - |
| `documented` | `confirmed` | Reopen the record | yes | `approve` | - |
| `not_a_breach` | `under_qualification` | Reopen a ruled-out qualification | yes | `approve` | - |
| any | `archived` | Archive | yes | `approve` | - |
| `archived` | `draft` | Restore | - | `approve` | - |

## post_incident_review

Run by `incidents.PostIncidentReview`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `scheduled` | Review scheduled | intermediate | yes | - | yes |
| `in_progress` | Review in progress | intermediate | yes | - | - |
| `submitted` | Review submitted | intermediate | yes | yes | - |
| `approved` | Review approved | intermediate | yes | yes | - |
| `effectiveness_verified` | Effectiveness verified | archived | yes | yes | - |
| `cancelled` | Review cancelled | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `scheduled` | Schedule the review | - | `create` | - |
| `scheduled` | `in_progress` | Start the review | - | `update` | - |
| `in_progress` | `submitted` | Submit the review | - | `update` | - |
| `submitted` | `approved` | Approve the review | yes | `validate` | - |
| `submitted` | `in_progress` | Send back for rework | yes | `update` | - |
| `approved` | `effectiveness_verified` | Verify effectiveness | yes | `validate` | - |
| `scheduled` | `cancelled` | Cancel the review | yes | `validate` | - |
| `in_progress` | `cancelled` | Cancel the review | yes | `validate` | - |
| any | `archived` | Archive | yes | `validate` | - |
| `archived` | `draft` | Restore | - | `validate` | - |

## risk

Run by `risks.Risk`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `identified` | Identified | intermediate | - | - | yes |
| `analyzed` | Analyzed | intermediate | yes | yes | - |
| `evaluated` | Evaluated | intermediate | yes | yes | - |
| `treatment_planned` | Treatment planned | intermediate | yes | yes | - |
| `treatment_in_progress` | Treatment in progress | intermediate | yes | yes | - |
| `treated` | Treated | intermediate | yes | yes | - |
| `accepted` | Accepted | intermediate | yes | yes | - |
| `closed` | Closed | archived | yes | - | - |
| `monitoring` | Monitoring | intermediate | yes | yes | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `identified` | Start | - | - | - |
| `identified` | `analyzed` | Analyzed | - | - | - |
| `analyzed` | `evaluated` | Evaluated | - | - | - |
| `evaluated` | `treatment_planned` | Treatment planned | - | - | - |
| `evaluated` | `accepted` | Accepted | - | - | - |
| `treatment_planned` | `treatment_in_progress` | Treatment in progress | - | - | - |
| `treatment_in_progress` | `treated` | Treated | - | - | - |
| `treated` | `accepted` | Accepted | - | - | - |
| `treated` | `monitoring` | Monitoring | - | - | - |
| `treated` | `closed` | Closed | - | - | - |
| `accepted` | `monitoring` | Monitoring | - | - | - |
| `accepted` | `closed` | Closed | - | - | - |
| `monitoring` | `analyzed` | Analyzed | - | - | - |
| `monitoring` | `closed` | Closed | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## risk_acceptance

Run by `risks.RiskAcceptance`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `active` | Active | intermediate | yes | - | yes |
| `expired` | Expired | intermediate | yes | - | - |
| `revoked` | Revoked | archived | yes | - | - |
| `renewed` | Renewed | intermediate | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `active` | Start | - | - | - |
| `active` | `expired` | Expired | - | - | - |
| `active` | `renewed` | Renewed | - | - | - |
| `active` | `revoked` | Revoked | - | - | - |
| `renewed` | `expired` | Expired | - | - | - |
| `renewed` | `revoked` | Revoked | - | - | - |
| `expired` | `renewed` | Renewed | - | - | - |
| `expired` | `revoked` | Revoked | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## risk_assessment

Run by `risks.RiskAssessment`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `in_progress` | In progress | intermediate | yes | - | - |
| `completed` | Completed | intermediate | yes | - | - |
| `validated` | Validated | intermediate | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `in_progress` | In progress | - | - | - |
| `in_progress` | `completed` | Completed | - | - | - |
| `completed` | `in_progress` | In progress | - | - | - |
| `completed` | `validated` | Validated | - | - | - |
| `validated` | `archived` | Archived | - | - | - |

## risk_treatment_plan

Run by `risks.RiskTreatmentPlan`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `planned` | Planned | intermediate | yes | yes | yes |
| `in_progress` | In progress | intermediate | yes | yes | - |
| `completed` | Completed | archived | yes | - | - |
| `cancelled` | Cancelled | archived | - | - | - |
| `overdue` | Overdue | intermediate | yes | yes | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `planned` | Start | - | - | - |
| `planned` | `in_progress` | In progress | - | - | - |
| `in_progress` | `completed` | Completed | - | - | - |
| `planned` | `overdue` | Overdue | - | - | - |
| `in_progress` | `overdue` | Overdue | - | - | - |
| `overdue` | `in_progress` | In progress | - | - | - |
| `overdue` | `completed` | Completed | - | - | - |
| `planned` | `cancelled` | Cancelled | - | - | - |
| `in_progress` | `cancelled` | Cancelled | - | - | - |
| `overdue` | `cancelled` | Cancelled | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## scope

Run by `context.Scope`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `definition` | Definition | intermediate | - | - | - |
| `validation` | Validation | intermediate | - | - | - |
| `in_force` | In force | intermediate | yes | yes | - |
| `review` | Review | intermediate | yes | yes | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `definition` | Start definition | - | - | - |
| `definition` | `validation` | Submit for validation | - | - | - |
| `validation` | `in_force` | Put in force | - | - | - |
| `in_force` | `review` | Start review | - | - | - |
| `review` | `in_force` | Complete review | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## security_event

Run by `incidents.SecurityEvent`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `reported` | Reported | intermediate | yes | - | yes |
| `under_assessment` | Under assessment | intermediate | yes | - | - |
| `confirmed_incident` | Promoted to incident | archived | yes | yes | - |
| `confirmed_weakness` | Confirmed weakness | archived | yes | yes | - |
| `discarded` | Discarded | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `reported` | Report the event | - | `create` | - |
| `reported` | `under_assessment` | Start the assessment | - | `update` | - |
| `under_assessment` | `confirmed_incident` | Promote to incident | yes | `validate` | - |
| `under_assessment` | `confirmed_weakness` | Record as a weakness | yes | `update` | - |
| `under_assessment` | `discarded` | Discard | yes | `validate` | - |
| `discarded` | `under_assessment` | Reopen the assessment | yes | `update` | - |
| any | `archived` | Archive | yes | `validate` | - |
| `archived` | `draft` | Restore | - | `validate` | - |

## site

Run by `context.Site`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `commissioning` | Commissioning | intermediate | - | - | - |
| `operational` | Operational | intermediate | yes | yes | - |
| `review` | Under review | intermediate | yes | yes | - |
| `decommissioned` | Decommissioned | intermediate | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `commissioning` | Start commissioning | - | - | - |
| `commissioning` | `operational` | Bring into service | - | - | - |
| `operational` | `review` | Start review | - | - | - |
| `review` | `operational` | Complete review | - | - | - |
| `operational` | `decommissioned` | Decommission | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## supplier

Run by `assets.Supplier`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `integration` | Onboarding | intermediate | yes | yes | - |
| `risk_questionnaire` | Risk questionnaire | intermediate | yes | yes | - |
| `evaluation` | Evaluation | intermediate | yes | yes | - |
| `compliant` | Compliant asset | intermediate | yes | yes | - |
| `non_compliant` | Non-compliant asset | intermediate | yes | yes | - |
| `compensatory_measures` | Compensatory measures | intermediate | yes | yes | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `integration` | Start onboarding | - | - | - |
| `integration` | `risk_questionnaire` | Send risk questionnaire | - | - | - |
| `risk_questionnaire` | `evaluation` | Start evaluation | - | - | - |
| `evaluation` | `compliant` | Mark compliant | - | - | - |
| `evaluation` | `non_compliant` | Mark non-compliant | - | - | - |
| `compliant` | `risk_questionnaire` | New review cycle | - | - | - |
| `non_compliant` | `compensatory_measures` | Add compensatory measures | - | - | - |
| `compensatory_measures` | `evaluation` | Re-evaluate | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## support_asset

Run by `assets.SupportAsset`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `in_stock` | In stock | intermediate | yes | yes | yes |
| `deployed` | Deployed | intermediate | yes | yes | - |
| `active` | Active | intermediate | yes | yes | yes |
| `under_maintenance` | Under maintenance | intermediate | yes | yes | - |
| `decommissioned` | Decommissioned | intermediate | yes | - | - |
| `disposed` | Disposed | intermediate | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `in_stock` | Receive | - | - | - |
| `in_stock` | `deployed` | Deploy | - | - | - |
| `deployed` | `active` | Commission | - | - | - |
| `active` | `under_maintenance` | Start maintenance | - | - | - |
| `under_maintenance` | `active` | Complete maintenance | - | - | - |
| `active` | `decommissioned` | Decommission | - | - | - |
| `under_maintenance` | `decommissioned` | Decommission | - | - | - |
| `decommissioned` | `disposed` | Dispose | - | - | - |
| `disposed` | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## trust_center_document_request

Run by `trust_center.DocumentRequest`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `pending` | Pending review | intermediate | - | - | yes |
| `approved` | Approved | intermediate | yes | - | - |
| `rejected` | Rejected | archived | - | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `pending` | Start | - | - | - |
| `pending` | `approved` | Approve | - | `approve` | - |
| `pending` | `rejected` | Reject | yes | `approve` | - |
| `approved` | `rejected` | Revoke access | yes | `approve` | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

## trust_center_publication

Run by `trust_center.TrustCenterCertification`, `trust_center.TrustCenterDocument`, `trust_center.TrustCenterMeasure`, `trust_center.TrustCenterSubprocessor`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `published` | Published | intermediate | yes | - | - |
| `unpublished` | Unpublished | intermediate | - | - | yes |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `published` | Publish | - | `approve` | - |
| `draft` | `archived` | Archive | - | `update` | - |
| `published` | `unpublished` | Unpublish | - | `approve` | - |
| `published` | `archived` | Archive | - | `approve` | - |
| `unpublished` | `published` | Publish | - | `approve` | - |
| `unpublished` | `archived` | Archive | - | `update` | - |

## vulnerability

Run by `risks.Vulnerability`.

### Steps

| Code | Label | Kind | In reports | Linkable | Deletable |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | draft | - | - | yes |
| `identified` | Identified | intermediate | yes | yes | yes |
| `confirmed` | Confirmed | intermediate | yes | yes | - |
| `mitigated` | Mitigated | intermediate | yes | yes | - |
| `accepted` | Accepted | intermediate | yes | yes | - |
| `closed` | Closed | archived | yes | - | - |
| `archived` | Archived | archived | - | - | - |

### Transitions

| From | To | Label | Comment required | Permission | Restricted to roles |
| --- | --- | --- | --- | --- | --- |
| `draft` | `identified` | Start | - | - | - |
| `identified` | `confirmed` | Confirmed | - | - | - |
| `identified` | `closed` | Closed | - | - | - |
| `confirmed` | `mitigated` | Mitigated | - | - | - |
| `confirmed` | `accepted` | Accepted | - | - | - |
| `mitigated` | `closed` | Closed | - | - | - |
| `accepted` | `closed` | Closed | - | - | - |
| any | `archived` | Archive | - | - | - |
| `archived` | `draft` | Restore | - | - | - |

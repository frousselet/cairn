<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the Django model registry by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Models

Every persisted model in the project, with the platform-wide behaviours it inherits. `BaseModel` gives a UUID primary key, timestamps, `created_by`, a lifecycle and versioning; `ScopedModel` adds the `scopes` many-to-many that drives tenancy; `ReferenceGeneratorMixin` issues the sequential business reference from a four-character prefix.

The field-by-field contract of each entity lives in its [specification](../../specs/README.md); this page is the inventory.

**114 models** are registered.

## Inventory

| App | Model | Table | Prefix | Lifecycle | Scoped | History | Fields |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | `AccessLog` | `accounts_accesslog` | - | - | - | - | 9 |
| accounts | `CalendarToken` | `accounts_calendartoken` | - | - | - | - | 7 |
| accounts | `CompanySettings` | `accounts_companysettings` | - | - | - | - | 12 |
| accounts | `Group` | `accounts_group` | - | - | - | - | 7 |
| accounts | `Notification` | `accounts_notification` | - | - | - | - | 12 |
| accounts | `Passkey` | `accounts_passkey` | - | - | - | - | 8 |
| accounts | `Permission` | `accounts_permission` | - | - | - | - | 8 |
| accounts | `SavedFilter` | `accounts_savedfilter` | - | - | - | - | 8 |
| accounts | `User` | `accounts_user` | - | - | - | - | 35 |
| assets | `AssetDependency` | `assets_assetdependency` | `ADEP` | - | - | yes | 13 |
| assets | `AssetGroup` | `assets_assetgroup` | `AGRP` | `default` | yes | yes | 12 |
| assets | `AssetValuation` | `assets_assetvaluation` | - | - | - | yes | 10 |
| assets | `Certificate` | `assets_certificate` | `CERT` | `certificate` | yes | yes | 19 |
| assets | `Contract` | `assets_contract` | `CTRT` | `contract` | yes | yes | 18 |
| assets | `EssentialAsset` | `assets_essentialasset` | `EAST` | `essential_asset` | yes | yes | 27 |
| assets | `SiteAssetDependency` | `assets_siteassetdependency` | `SADP` | - | - | yes | 13 |
| assets | `SiteSupplierDependency` | `assets_sitesupplierdependency` | `SSDP` | - | - | yes | 13 |
| assets | `SupplierContact` | `assets_suppliercontact` | - | - | - | yes | 10 |
| assets | `SupplierDependency` | `assets_supplierdependency` | `SDEP` | - | - | yes | 13 |
| assets | `SupplierRequirementReview` | `assets_supplierrequirementreview` | - | - | - | - | 10 |
| assets | `SupplierRequirement` | `assets_supplierrequirement` | - | - | - | - | 13 |
| assets | `SupplierSubprocessor` | `assets_suppliersubprocessor` | `SSPR` | - | - | yes | 14 |
| assets | `SupplierTypeRequirement` | `assets_suppliertyperequirement` | - | - | - | - | 6 |
| assets | `SupplierType` | `assets_suppliertype` | `SPTY` | - | - | - | 6 |
| assets | `Supplier` | `assets_supplier` | `SUPP` | `supplier` | yes | yes | 30 |
| assets | `SupportAsset` | `assets_supportasset` | `SAST` | `support_asset` | yes | yes | 33 |
| assistant | `AssistantFeedback` | `assistant_assistantfeedback` | - | - | - | - | 16 |
| assistant | `SemanticIndex` | `assistant_semanticindex` | - | - | - | - | 8 |
| compliance | `ActionPlanComment` | `compliance_actionplancomment` | - | - | - | - | 7 |
| compliance | `ActionPlanTransition` | `compliance_actionplantransition` | - | - | - | - | 8 |
| compliance | `AssessmentResultAttachment` | `compliance_assessmentresultattachment` | - | - | - | - | 7 |
| compliance | `AssessmentResult` | `compliance_assessmentresult` | - | - | - | yes | 12 |
| compliance | `ComplianceActionPlan` | `compliance_complianceactionplan` | `CAPL` | `action_plan` | yes | yes | 19 |
| compliance | `ComplianceAssessment` | `compliance_complianceassessment` | `CAST` | `compliance_assessment` | yes | yes | 24 |
| compliance | `Finding` | `compliance_finding` | - | `default` | - | yes | 18 |
| compliance | `Framework` | `compliance_framework` | `FWRK` | `default` | yes | yes | 32 |
| compliance | `RequirementMapping` | `compliance_requirementmapping` | - | - | - | yes | 10 |
| compliance | `Requirement` | `compliance_requirement` | `REQT` | `default` | - | yes | 27 |
| compliance | `Section` | `compliance_section` | - | - | - | yes | 10 |
| context | `Activity` | `context_activity` | `ACTV` | `default` | yes | yes | 14 |
| context | `IndicatorMeasurement` | `context_indicatormeasurement` | - | - | - | - | 6 |
| context | `Indicator` | `context_indicator` | `INDC` | `default` | yes | yes | 26 |
| context | `Issue` | `context_issue` | `ISSU` | `default` | yes | yes | 16 |
| context | `Objective` | `context_objective` | `OBJT` | `default` | yes | yes | 23 |
| context | `Responsibility` | `context_responsibility` | - | - | - | yes | 7 |
| context | `Role` | `context_role` | `ROLE` | `default` | yes | yes | 13 |
| context | `Scope` | `context_scope` | `SCOP` | `scope` | - | yes | 18 |
| context | `Site` | `context_site` | `SITE` | `site` | yes | yes | 12 |
| context | `StakeholderExpectation` | `context_stakeholderexpectation` | - | - | - | yes | 8 |
| context | `StakeholderFeedback` | `context_stakeholderfeedback` | `FBCK` | `default` | yes | yes | 16 |
| context | `Stakeholder` | `context_stakeholder` | `STKH` | `default` | yes | yes | 18 |
| context | `SwotAnalysis` | `context_swotanalysis` | `SWOT` | `default` | yes | yes | 13 |
| context | `SwotItem` | `context_swotitem` | - | - | - | yes | 8 |
| context | `SwotStrategy` | `context_swotstrategy` | - | - | - | yes | 7 |
| context | `Tag` | `context_tag` | - | - | - | - | 4 |
| core | `LifecycleDefinition` | `core_lifecycledefinition` | - | - | - | - | 8 |
| core | `LifecycleEvent` | `core_lifecycleevent` | - | - | - | - | 10 |
| helpers | `HelpContent` | `helpers_helpcontent` | - | - | - | - | 6 |
| incidents | `EvidenceCustodyEvent` | `incidents_evidencecustodyevent` | - | - | - | yes | 16 |
| incidents | `IncidentEvidence` | `incidents_incidentevidence` | `EVID` | `incident_evidence` | - | yes | 30 |
| incidents | `IncidentNotification` | `incidents_incidentnotification` | `INOT` | `incident_notification` | - | yes | 40 |
| incidents | `IncidentResponseAction` | `incidents_incidentresponseaction` | `IRAC` | - | - | yes | 17 |
| incidents | `IncidentResponsePlan` | `incidents_incidentresponseplan` | `IRPL` | `default` | yes | yes | 22 |
| incidents | `IncidentTimelineEntry` | `incidents_incidenttimelineentry` | - | - | - | yes | 17 |
| incidents | `Incident` | `incidents_incident` | `INCD` | `incident` | yes | yes | 45 |
| incidents | `NotificationFiling` | `incidents_notificationfiling` | `NFIL` | - | - | yes | 20 |
| incidents | `PersonalDataBreach` | `incidents_personaldatabreach` | `PDBR` | `personal_data_breach` | - | yes | 29 |
| incidents | `PostIncidentReview` | `incidents_postincidentreview` | `PIRV` | `post_incident_review` | yes | yes | 29 |
| incidents | `ReportingAuthority` | `incidents_reportingauthority` | `RGAU` | `default` | - | yes | 18 |
| incidents | `ReportingObligationTemplate` | `incidents_reportingobligationtemplate` | `ROBT` | `default` | - | yes | 26 |
| incidents | `SecurityEvent` | `incidents_securityevent` | `EVNT` | `security_event` | yes | yes | 27 |
| mcp | `OAuthAccessToken` | `mcp_oauthaccesstoken` | - | - | - | - | 5 |
| mcp | `OAuthApplication` | `mcp_oauthapplication` | - | - | - | - | 11 |
| mcp | `OAuthAuthorizationCode` | `mcp_oauthauthorizationcode` | - | - | - | - | 11 |
| reports | `IsmsChange` | `reports_ismschange` | - | - | - | yes | 14 |
| reports | `ManagementReviewComment` | `reports_managementreviewcomment` | - | - | - | - | 5 |
| reports | `ManagementReviewDecision` | `reports_managementreviewdecision` | - | - | - | yes | 20 |
| reports | `ManagementReviewParticipant` | `reports_managementreviewparticipant` | - | - | - | - | 9 |
| reports | `ManagementReviewTransition` | `reports_managementreviewtransition` | - | - | - | - | 7 |
| reports | `ManagementReview` | `reports_managementreview` | `MRVW` | `management_review` | yes | yes | 23 |
| reports | `Report` | `reports_report` | - | - | - | yes | 10 |
| risks | `AttackPathStep` | `risks_attackpathstep` | `EAPS` | `default` | - | yes | 13 |
| risks | `AttackTechnique` | `risks_attacktechnique` | `EATT` | `default` | - | yes | 15 |
| risks | `BaselineGap` | `risks_baselinegap` | `EBGP` | `ebios_baseline_gap` | - | yes | 14 |
| risks | `EbiosSummary` | `risks_ebiossummary` | `ESUM` | `ebios_summary` | - | yes | 17 |
| risks | `EbiosWorkshopProgress` | `risks_ebiosworkshopprogress` | `EWSP` | `ebios_workshop` | - | yes | 17 |
| risks | `EcosystemStakeholder` | `risks_ecosystemstakeholder` | `EECS` | `default` | - | yes | 22 |
| risks | `FearedEvent` | `risks_fearedevent` | `EFER` | `default` | - | yes | 17 |
| risks | `ISO27005Risk` | `risks_iso27005risk` | `I27R` | `default` | - | yes | 22 |
| risks | `MitreAttackTechnique` | `risks_mitreattacktechnique` | - | - | - | - | 11 |
| risks | `OperationalScenario` | `risks_operationalscenario` | `EOPS` | `default` | - | yes | 21 |
| risks | `PACSMeasure` | `risks_pacsmeasure` | `EPAC` | `ebios_pacs_measure` | - | yes | 20 |
| risks | `RiskAcceptance` | `risks_riskacceptance` | `RACC` | `risk_acceptance` | - | yes | 15 |
| risks | `RiskAssessment` | `risks_riskassessment` | `RASS` | `risk_assessment` | yes | yes | 17 |
| risks | `RiskCriteria` | `risks_riskcriteria` | `RCRT` | `default` | yes | yes | 12 |
| risks | `RiskLevel` | `risks_risklevel` | - | - | - | - | 7 |
| risks | `RiskSourceObjectivePair` | `risks_risksourceobjectivepair` | `ESOV` | `default` | - | yes | 15 |
| risks | `RiskSource` | `risks_risksource` | `ERSC` | `default` | - | yes | 20 |
| risks | `RiskTreatmentPlan` | `risks_risktreatmentplan` | `RTPL` | `risk_treatment_plan` | - | yes | 20 |
| risks | `Risk` | `risks_risk` | `RISK` | `risk` | - | yes | 31 |
| risks | `ScaleLevel` | `risks_scalelevel` | - | - | - | - | 7 |
| risks | `SecurityBaseline` | `risks_securitybaseline` | `EBSL` | `ebios_security_baseline` | - | yes | 9 |
| risks | `StrategicScenario` | `risks_strategicscenario` | `ESTS` | `default` | - | yes | 21 |
| risks | `StudyFramework` | `risks_studyframework` | `EFRA` | `ebios_study_framework` | - | yes | 17 |
| risks | `TargetedObjective` | `risks_targetedobjective` | `ETOV` | `default` | - | yes | 13 |
| risks | `Threat` | `risks_threat` | `THRT` | `default` | yes | yes | 15 |
| risks | `TreatmentAction` | `risks_treatmentaction` | - | - | - | - | 10 |
| risks | `Vulnerability` | `risks_vulnerability` | `VULN` | `vulnerability` | yes | yes | 15 |
| trust_center | `DocumentRequest` | `trust_center_documentrequest` | `DREQ` | `trust_center_document_request` | - | yes | 22 |
| trust_center | `TrustCenterCertification` | `trust_center_trustcentercertification` | `TCCE` | `trust_center_publication` | - | yes | 12 |
| trust_center | `TrustCenterDocument` | `trust_center_trustcenterdocument` | `TCDO` | `trust_center_publication` | - | yes | 16 |
| trust_center | `TrustCenterMeasure` | `trust_center_trustcentermeasure` | `TCME` | `trust_center_publication` | - | yes | 12 |
| trust_center | `TrustCenterSettings` | `trust_center_trustcentersettings` | - | - | - | - | 10 |
| trust_center | `TrustCenterSubprocessor` | `trust_center_trustcentersubprocessor` | `TCSP` | `trust_center_publication` | - | yes | 13 |

<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the URL resolver (`core/urls.py` and each app's `api/urls.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# REST endpoints

The complete route table under `/api/v1/`. Authentication, pagination, filtering and the error contract are documented in [../rest-api.md](../rest-api.md); the field-level contract of each resource is in its [specification](../../specs/README.md).

**428 routes** are published across **21 groups**. Every route also answers at a `.<format>` suffix (`.json`, `.api`), which is omitted here.

## Groups

| Group | Routes |
| --- | --- |
| [`access-logs`](#access-logs) | 2 |
| [`assets`](#assets) | 68 |
| [`assistant`](#assistant) | 7 |
| [`auth`](#auth) | 4 |
| [`company-settings`](#company-settings) | 1 |
| [`compliance`](#compliance) | 36 |
| [`context`](#context) | 68 |
| [`dashboard-layout`](#dashboard-layout) | 1 |
| [`dependencies`](#dependencies) | 1 |
| [`groups`](#groups) | 4 |
| [`incidents`](#incidents) | 68 |
| [`mcp`](#mcp) | 1 |
| [`notifications`](#notifications) | 5 |
| [`oauth`](#oauth) | 4 |
| [`permissions`](#permissions) | 3 |
| [`reports`](#reports) | 17 |
| [`risks`](#risks) | 115 |
| [`root`](#root) | 2 |
| [`saved-filters`](#saved-filters) | 2 |
| [`trust-center`](#trust-center) | 14 |
| [`users`](#users) | 5 |

## access-logs

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/access-logs/` | GET | `accounts.api.views.AccessLogViewSet` | `access-log-list` |
| `/api/v1/access-logs/<pk>/` | GET | `accounts.api.views.AccessLogViewSet` | `access-log-detail` |

## assets

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/assets/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/assets/certificates/` | GET, POST | `assets.api.views.CertificateViewSet` | `certificate-list` |
| `/api/v1/assets/certificates/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.CertificateViewSet` | `certificate-detail` |
| `/api/v1/assets/certificates/<pk>/history/` | GET | `assets.api.views.CertificateViewSet` | `certificate-history` |
| `/api/v1/assets/certificates/<pk>/transition/` | GET, POST | `assets.api.views.CertificateViewSet` | `certificate-transition` |
| `/api/v1/assets/certificates/batch/` | POST | `assets.api.views.CertificateViewSet` | `certificate-batch-create` |
| `/api/v1/assets/contracts/` | GET, POST | `assets.api.views.ContractViewSet` | `contract-list` |
| `/api/v1/assets/contracts/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.ContractViewSet` | `contract-detail` |
| `/api/v1/assets/contracts/<pk>/history/` | GET | `assets.api.views.ContractViewSet` | `contract-history` |
| `/api/v1/assets/contracts/<pk>/transition/` | GET, POST | `assets.api.views.ContractViewSet` | `contract-transition` |
| `/api/v1/assets/contracts/batch/` | POST | `assets.api.views.ContractViewSet` | `contract-batch-create` |
| `/api/v1/assets/dependencies/` | GET, POST | `assets.api.views.AssetDependencyViewSet` | `assetdependency-list` |
| `/api/v1/assets/dependencies/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.AssetDependencyViewSet` | `assetdependency-detail` |
| `/api/v1/assets/dependencies/<pk>/history/` | GET | `assets.api.views.AssetDependencyViewSet` | `assetdependency-history` |
| `/api/v1/assets/dependencies/<pk>/transition/` | GET, POST | `assets.api.views.AssetDependencyViewSet` | `assetdependency-transition` |
| `/api/v1/assets/dependencies/batch/` | POST | `assets.api.views.AssetDependencyViewSet` | `assetdependency-batch-create` |
| `/api/v1/assets/dependencies/detect-spof/` | GET, POST | `assets.api.views.AssetDependencyViewSet` | `assetdependency-detect-spof` |
| `/api/v1/assets/dependencies/graph/` | GET | `assets.api.views.AssetDependencyViewSet` | `assetdependency-graph` |
| `/api/v1/assets/dependencies/spof/` | GET | `assets.api.views.AssetDependencyViewSet` | `assetdependency-spof` |
| `/api/v1/assets/essential-assets/` | GET, POST | `assets.api.views.EssentialAssetViewSet` | `essentialasset-list` |
| `/api/v1/assets/essential-assets/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.EssentialAssetViewSet` | `essentialasset-detail` |
| `/api/v1/assets/essential-assets/<pk>/dependencies/` | GET | `assets.api.views.EssentialAssetViewSet` | `essentialasset-dependencies` |
| `/api/v1/assets/essential-assets/<pk>/history/` | GET | `assets.api.views.EssentialAssetViewSet` | `essentialasset-history` |
| `/api/v1/assets/essential-assets/<pk>/supporting-assets/` | GET | `assets.api.views.EssentialAssetViewSet` | `essentialasset-supporting-assets` |
| `/api/v1/assets/essential-assets/<pk>/transition/` | GET, POST | `assets.api.views.EssentialAssetViewSet` | `essentialasset-transition` |
| `/api/v1/assets/essential-assets/<pk>/valuations/` | GET, POST | `assets.api.views.EssentialAssetViewSet` | `essentialasset-valuations` |
| `/api/v1/assets/essential-assets/batch/` | POST | `assets.api.views.EssentialAssetViewSet` | `essentialasset-batch-create` |
| `/api/v1/assets/essential-assets/dashboard/` | GET | `assets.api.views.EssentialAssetViewSet` | `essentialasset-dashboard` |
| `/api/v1/assets/groups/` | GET, POST | `assets.api.views.AssetGroupViewSet` | `assetgroup-list` |
| `/api/v1/assets/groups/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.AssetGroupViewSet` | `assetgroup-detail` |
| `/api/v1/assets/groups/<pk>/history/` | GET | `assets.api.views.AssetGroupViewSet` | `assetgroup-history` |
| `/api/v1/assets/groups/<pk>/members/` | GET, POST | `assets.api.views.AssetGroupViewSet` | `assetgroup-members` |
| `/api/v1/assets/groups/<pk>/members/<asset_id>/` | DELETE | `assets.api.views.AssetGroupViewSet` | `assetgroup-remove-member` |
| `/api/v1/assets/groups/<pk>/transition/` | GET, POST | `assets.api.views.AssetGroupViewSet` | `assetgroup-transition` |
| `/api/v1/assets/supplier-contacts/` | GET, POST | `assets.api.views.SupplierContactViewSet` | `suppliercontact-list` |
| `/api/v1/assets/supplier-contacts/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.SupplierContactViewSet` | `suppliercontact-detail` |
| `/api/v1/assets/supplier-dependencies/` | GET, POST | `assets.api.views.SupplierDependencyViewSet` | `supplierdependency-list` |
| `/api/v1/assets/supplier-dependencies/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.SupplierDependencyViewSet` | `supplierdependency-detail` |
| `/api/v1/assets/supplier-dependencies/<pk>/history/` | GET | `assets.api.views.SupplierDependencyViewSet` | `supplierdependency-history` |
| `/api/v1/assets/supplier-dependencies/<pk>/transition/` | GET, POST | `assets.api.views.SupplierDependencyViewSet` | `supplierdependency-transition` |
| `/api/v1/assets/supplier-dependencies/batch/` | POST | `assets.api.views.SupplierDependencyViewSet` | `supplierdependency-batch-create` |
| `/api/v1/assets/supplier-subprocessors/` | GET, POST | `assets.api.views.SupplierSubprocessorViewSet` | `suppliersubprocessor-list` |
| `/api/v1/assets/supplier-subprocessors/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.SupplierSubprocessorViewSet` | `suppliersubprocessor-detail` |
| `/api/v1/assets/supplier-subprocessors/<pk>/history/` | GET | `assets.api.views.SupplierSubprocessorViewSet` | `suppliersubprocessor-history` |
| `/api/v1/assets/supplier-subprocessors/batch/` | POST | `assets.api.views.SupplierSubprocessorViewSet` | `suppliersubprocessor-batch-create` |
| `/api/v1/assets/suppliers/` | GET, POST | `assets.api.views.SupplierViewSet` | `supplier-list` |
| `/api/v1/assets/suppliers/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.SupplierViewSet` | `supplier-detail` |
| `/api/v1/assets/suppliers/<pk>/archive/` | POST | `assets.api.views.SupplierViewSet` | `supplier-archive` |
| `/api/v1/assets/suppliers/<pk>/contacts/` | GET, POST | `assets.api.views.SupplierViewSet` | `supplier-contacts` |
| `/api/v1/assets/suppliers/<pk>/history/` | GET | `assets.api.views.SupplierViewSet` | `supplier-history` |
| `/api/v1/assets/suppliers/<pk>/requirements/` | GET, POST | `assets.api.views.SupplierViewSet` | `supplier-requirements` |
| `/api/v1/assets/suppliers/<pk>/subprocessors/` | GET, POST | `assets.api.views.SupplierViewSet` | `supplier-subprocessors` |
| `/api/v1/assets/suppliers/<pk>/subsidiaries/` | GET | `assets.api.views.SupplierViewSet` | `supplier-subsidiaries` |
| `/api/v1/assets/suppliers/<pk>/transition/` | GET, POST | `assets.api.views.SupplierViewSet` | `supplier-transition` |
| `/api/v1/assets/suppliers/batch/` | POST | `assets.api.views.SupplierViewSet` | `supplier-batch-create` |
| `/api/v1/assets/suppliers/dashboard/` | GET | `assets.api.views.SupplierViewSet` | `supplier-dashboard` |
| `/api/v1/assets/support-assets/` | GET, POST | `assets.api.views.SupportAssetViewSet` | `supportasset-list` |
| `/api/v1/assets/support-assets/<pk>/` | DELETE, GET, PATCH, PUT | `assets.api.views.SupportAssetViewSet` | `supportasset-detail` |
| `/api/v1/assets/support-assets/<pk>/children/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-children` |
| `/api/v1/assets/support-assets/<pk>/dependencies/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-dependencies` |
| `/api/v1/assets/support-assets/<pk>/essential-assets/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-essential-assets` |
| `/api/v1/assets/support-assets/<pk>/history/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-history` |
| `/api/v1/assets/support-assets/<pk>/inherited-dic/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-inherited-dic` |
| `/api/v1/assets/support-assets/<pk>/transition/` | GET, POST | `assets.api.views.SupportAssetViewSet` | `supportasset-transition` |
| `/api/v1/assets/support-assets/batch/` | POST | `assets.api.views.SupportAssetViewSet` | `supportasset-batch-create` |
| `/api/v1/assets/support-assets/dashboard/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-dashboard` |
| `/api/v1/assets/support-assets/end-of-life/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-end-of-life` |
| `/api/v1/assets/support-assets/tree/` | GET | `assets.api.views.SupportAssetViewSet` | `supportasset-tree` |

## assistant

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/assistant/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/assistant/ask/` | POST, OPTIONS | `assistant.api.views.AskAssistantApiView` | `assistant-api-ask` |
| `/api/v1/assistant/feedback/` | GET, POST | `assistant.api.views.AssistantFeedbackViewSet` | `assistant-feedback-list` |
| `/api/v1/assistant/feedback/<pk>/` | GET | `assistant.api.views.AssistantFeedbackViewSet` | `assistant-feedback-detail` |
| `/api/v1/assistant/feedback/<pk>/resolve/` | POST | `assistant.api.views.AssistantFeedbackViewSet` | `assistant-feedback-resolve` |
| `/api/v1/assistant/feedback/<pk>/unresolve/` | POST | `assistant.api.views.AssistantFeedbackViewSet` | `assistant-feedback-unresolve` |
| `/api/v1/assistant/feedback/export/` | GET | `assistant.api.views.AssistantFeedbackViewSet` | `assistant-feedback-export` |

## auth

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/auth/login/` | POST, OPTIONS | `accounts.api.views.LoginAPIView` | `api-login` |
| `/api/v1/auth/logout/` | POST, OPTIONS | `accounts.api.views.LogoutAPIView` | `api-logout` |
| `/api/v1/auth/me/` | GET, PATCH, OPTIONS | `accounts.api.views.MeAPIView` | `api-me` |
| `/api/v1/auth/refresh/` | POST, OPTIONS | `accounts.api.views.TokenRefreshAPIView` | `api-token-refresh` |

## company-settings

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/company-settings/` | GET, PATCH, OPTIONS | `accounts.api.views.CompanySettingsAPIView` | `api-company-settings` |

## compliance

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/compliance/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/compliance/action-plans/` | GET, POST | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-list` |
| `/api/v1/compliance/action-plans/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-detail` |
| `/api/v1/compliance/action-plans/<pk>/comments/` | GET, POST | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-comments` |
| `/api/v1/compliance/action-plans/<pk>/history/` | GET | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-history` |
| `/api/v1/compliance/action-plans/<pk>/transition/` | POST | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-transition` |
| `/api/v1/compliance/action-plans/<pk>/transitions/` | GET | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-transitions` |
| `/api/v1/compliance/action-plans/dashboard/` | GET | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-dashboard` |
| `/api/v1/compliance/action-plans/kanban/` | GET | `compliance.api.views.ComplianceActionPlanViewSet` | `complianceactionplan-kanban` |
| `/api/v1/compliance/assessments/` | GET, POST | `compliance.api.views.ComplianceAssessmentViewSet` | `complianceassessment-list` |
| `/api/v1/compliance/assessments/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.ComplianceAssessmentViewSet` | `complianceassessment-detail` |
| `/api/v1/compliance/assessments/<pk>/history/` | GET | `compliance.api.views.ComplianceAssessmentViewSet` | `complianceassessment-history` |
| `/api/v1/compliance/assessments/<pk>/summary/` | GET | `compliance.api.views.ComplianceAssessmentViewSet` | `complianceassessment-summary` |
| `/api/v1/compliance/assessments/<pk>/transition/` | POST | `compliance.api.views.ComplianceAssessmentViewSet` | `complianceassessment-transition` |
| `/api/v1/compliance/assessments/<uuid:assessment_pk>/findings/` | GET, POST | `compliance.api.views.FindingViewSet` | `assessment-findings-list` |
| `/api/v1/compliance/assessments/<uuid:assessment_pk>/findings/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.FindingViewSet` | `assessment-findings-detail` |
| `/api/v1/compliance/assessments/<uuid:assessment_pk>/results/` | GET, POST | `compliance.api.views.AssessmentResultViewSet` | `assessment-results-list` |
| `/api/v1/compliance/assessments/<uuid:assessment_pk>/results/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.AssessmentResultViewSet` | `assessment-results-detail` |
| `/api/v1/compliance/frameworks/` | GET, POST | `compliance.api.views.FrameworkViewSet` | `framework-list` |
| `/api/v1/compliance/frameworks/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.FrameworkViewSet` | `framework-detail` |
| `/api/v1/compliance/frameworks/<pk>/compliance_summary/` | GET | `compliance.api.views.FrameworkViewSet` | `framework-compliance-summary` |
| `/api/v1/compliance/frameworks/<pk>/history/` | GET | `compliance.api.views.FrameworkViewSet` | `framework-history` |
| `/api/v1/compliance/frameworks/<pk>/transition/` | GET, POST | `compliance.api.views.FrameworkViewSet` | `framework-transition` |
| `/api/v1/compliance/mappings/` | GET, POST | `compliance.api.views.RequirementMappingViewSet` | `requirementmapping-list` |
| `/api/v1/compliance/mappings/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.RequirementMappingViewSet` | `requirementmapping-detail` |
| `/api/v1/compliance/requirements/` | GET, POST | `compliance.api.views.RequirementViewSet` | `requirement-list` |
| `/api/v1/compliance/requirements/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.RequirementViewSet` | `requirement-detail` |
| `/api/v1/compliance/requirements/<pk>/assess/` | PATCH | `compliance.api.views.RequirementViewSet` | `requirement-assess` |
| `/api/v1/compliance/requirements/<pk>/history/` | GET | `compliance.api.views.RequirementViewSet` | `requirement-history` |
| `/api/v1/compliance/requirements/<pk>/transition/` | GET, POST | `compliance.api.views.RequirementViewSet` | `requirement-transition` |
| `/api/v1/compliance/requirements/batch/` | POST | `compliance.api.views.RequirementViewSet` | `requirement-batch-create` |
| `/api/v1/compliance/sections/` | GET, POST | `compliance.api.views.SectionViewSet` | `section-list` |
| `/api/v1/compliance/sections/<pk>/` | DELETE, GET, PATCH, PUT | `compliance.api.views.SectionViewSet` | `section-detail` |
| `/api/v1/compliance/sections/<pk>/children/` | GET | `compliance.api.views.SectionViewSet` | `section-children` |
| `/api/v1/compliance/sections/batch/` | POST | `compliance.api.views.SectionViewSet` | `section-batch-create` |
| `/api/v1/compliance/sections/tree/` | GET | `compliance.api.views.SectionViewSet` | `section-tree` |

## context

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/context/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/context/activities/` | GET, POST | `context.api.views.ActivityViewSet` | `activity-list` |
| `/api/v1/context/activities/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.ActivityViewSet` | `activity-detail` |
| `/api/v1/context/activities/<pk>/children/` | GET | `context.api.views.ActivityViewSet` | `activity-children` |
| `/api/v1/context/activities/<pk>/history/` | GET | `context.api.views.ActivityViewSet` | `activity-history` |
| `/api/v1/context/activities/<pk>/transition/` | GET, POST | `context.api.views.ActivityViewSet` | `activity-transition` |
| `/api/v1/context/activities/tree/` | GET | `context.api.views.ActivityViewSet` | `activity-tree` |
| `/api/v1/context/indicators/` | GET, POST | `context.api.views.IndicatorViewSet` | `indicator-list` |
| `/api/v1/context/indicators/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.IndicatorViewSet` | `indicator-detail` |
| `/api/v1/context/indicators/<pk>/history/` | GET | `context.api.views.IndicatorViewSet` | `indicator-history` |
| `/api/v1/context/indicators/<pk>/record/` | POST | `context.api.views.IndicatorViewSet` | `indicator-record` |
| `/api/v1/context/indicators/<pk>/refresh/` | POST | `context.api.views.IndicatorViewSet` | `indicator-refresh` |
| `/api/v1/context/indicators/<pk>/transition/` | GET, POST | `context.api.views.IndicatorViewSet` | `indicator-transition` |
| `/api/v1/context/indicators/<uuid:indicator_pk>/measurements/` | GET, POST | `context.api.views.IndicatorMeasurementViewSet` | `indicator-measurements-list` |
| `/api/v1/context/indicators/<uuid:indicator_pk>/measurements/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.IndicatorMeasurementViewSet` | `indicator-measurements-detail` |
| `/api/v1/context/issues/` | GET, POST | `context.api.views.IssueViewSet` | `issue-list` |
| `/api/v1/context/issues/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.IssueViewSet` | `issue-detail` |
| `/api/v1/context/issues/<pk>/history/` | GET | `context.api.views.IssueViewSet` | `issue-history` |
| `/api/v1/context/issues/<pk>/transition/` | GET, POST | `context.api.views.IssueViewSet` | `issue-transition` |
| `/api/v1/context/objectives/` | GET, POST | `context.api.views.ObjectiveViewSet` | `objective-list` |
| `/api/v1/context/objectives/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.ObjectiveViewSet` | `objective-detail` |
| `/api/v1/context/objectives/<pk>/children/` | GET | `context.api.views.ObjectiveViewSet` | `objective-children` |
| `/api/v1/context/objectives/<pk>/history/` | GET | `context.api.views.ObjectiveViewSet` | `objective-history` |
| `/api/v1/context/objectives/<pk>/transition/` | GET, POST | `context.api.views.ObjectiveViewSet` | `objective-transition` |
| `/api/v1/context/objectives/dashboard/` | GET | `context.api.views.ObjectiveViewSet` | `objective-dashboard` |
| `/api/v1/context/objectives/tree/` | GET | `context.api.views.ObjectiveViewSet` | `objective-tree` |
| `/api/v1/context/roles/` | GET, POST | `context.api.views.RoleViewSet` | `role-list` |
| `/api/v1/context/roles/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.RoleViewSet` | `role-detail` |
| `/api/v1/context/roles/<pk>/assign/` | POST | `context.api.views.RoleViewSet` | `role-assign` |
| `/api/v1/context/roles/<pk>/assign/<user_id>/` | DELETE | `context.api.views.RoleViewSet` | `role-unassign` |
| `/api/v1/context/roles/<pk>/history/` | GET | `context.api.views.RoleViewSet` | `role-history` |
| `/api/v1/context/roles/<pk>/transition/` | GET, POST | `context.api.views.RoleViewSet` | `role-transition` |
| `/api/v1/context/roles/<uuid:role_pk>/responsibilities/` | GET, POST | `context.api.views.ResponsibilityViewSet` | `role-responsibilities-list` |
| `/api/v1/context/roles/<uuid:role_pk>/responsibilities/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.ResponsibilityViewSet` | `role-responsibilities-detail` |
| `/api/v1/context/roles/compliance-check/` | GET | `context.api.views.RoleViewSet` | `role-compliance-check` |
| `/api/v1/context/scopes/` | GET, POST | `context.api.views.ScopeViewSet` | `scope-list` |
| `/api/v1/context/scopes/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.ScopeViewSet` | `scope-detail` |
| `/api/v1/context/scopes/<pk>/archive/` | POST | `context.api.views.ScopeViewSet` | `scope-archive` |
| `/api/v1/context/scopes/<pk>/history/` | GET | `context.api.views.ScopeViewSet` | `scope-history` |
| `/api/v1/context/scopes/<pk>/transition/` | GET, POST | `context.api.views.ScopeViewSet` | `scope-transition` |
| `/api/v1/context/sites/` | GET, POST | `context.api.views.SiteViewSet` | `site-list` |
| `/api/v1/context/sites/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.SiteViewSet` | `site-detail` |
| `/api/v1/context/sites/<pk>/history/` | GET | `context.api.views.SiteViewSet` | `site-history` |
| `/api/v1/context/sites/<pk>/transition/` | GET, POST | `context.api.views.SiteViewSet` | `site-transition` |
| `/api/v1/context/stakeholder-feedback/` | GET, POST | `context.api.views.StakeholderFeedbackViewSet` | `stakeholderfeedback-list` |
| `/api/v1/context/stakeholder-feedback/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.StakeholderFeedbackViewSet` | `stakeholderfeedback-detail` |
| `/api/v1/context/stakeholder-feedback/<pk>/history/` | GET | `context.api.views.StakeholderFeedbackViewSet` | `stakeholderfeedback-history` |
| `/api/v1/context/stakeholders/` | GET, POST | `context.api.views.StakeholderViewSet` | `stakeholder-list` |
| `/api/v1/context/stakeholders/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.StakeholderViewSet` | `stakeholder-detail` |
| `/api/v1/context/stakeholders/<pk>/history/` | GET | `context.api.views.StakeholderViewSet` | `stakeholder-history` |
| `/api/v1/context/stakeholders/<pk>/transition/` | GET, POST | `context.api.views.StakeholderViewSet` | `stakeholder-transition` |
| `/api/v1/context/stakeholders/<uuid:stakeholder_pk>/expectations/` | GET, POST | `context.api.views.StakeholderExpectationViewSet` | `stakeholder-expectations-list` |
| `/api/v1/context/stakeholders/<uuid:stakeholder_pk>/expectations/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.StakeholderExpectationViewSet` | `stakeholder-expectations-detail` |
| `/api/v1/context/stakeholders/batch/` | POST | `context.api.views.StakeholderViewSet` | `stakeholder-batch-create` |
| `/api/v1/context/stakeholders/matrix/` | GET | `context.api.views.StakeholderViewSet` | `stakeholder-matrix` |
| `/api/v1/context/swot-analyses/` | GET, POST | `context.api.views.SwotAnalysisViewSet` | `swotanalysis-list` |
| `/api/v1/context/swot-analyses/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.SwotAnalysisViewSet` | `swotanalysis-detail` |
| `/api/v1/context/swot-analyses/<pk>/history/` | GET | `context.api.views.SwotAnalysisViewSet` | `swotanalysis-history` |
| `/api/v1/context/swot-analyses/<pk>/transition/` | GET, POST | `context.api.views.SwotAnalysisViewSet` | `swotanalysis-transition` |
| `/api/v1/context/swot-analyses/<pk>/validate/` | POST | `context.api.views.SwotAnalysisViewSet` | `swotanalysis-validate` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/items/` | GET, POST | `context.api.views.SwotItemViewSet` | `swot-items-list` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/items/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.SwotItemViewSet` | `swot-items-detail` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/items/reorder/` | PATCH | `context.api.views.SwotItemViewSet` | `swot-items-reorder` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/strategies/` | GET, POST | `context.api.views.SwotStrategyViewSet` | `swot-strategies-list` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/strategies/<uuid:pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.SwotStrategyViewSet` | `swot-strategies-detail` |
| `/api/v1/context/swot-analyses/<uuid:analysis_pk>/strategies/reorder/` | PATCH | `context.api.views.SwotStrategyViewSet` | `swot-strategies-reorder` |
| `/api/v1/context/tags/` | GET, POST | `context.api.views.TagViewSet` | `tag-list` |
| `/api/v1/context/tags/<pk>/` | DELETE, GET, PATCH, PUT | `context.api.views.TagViewSet` | `tag-detail` |

## dashboard-layout

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/dashboard-layout/` | GET, PUT, OPTIONS | `accounts.api.views.DashboardLayoutAPIView` | `api-dashboard-layout` |

## dependencies

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/dependencies/` | GET, OPTIONS | `accounts.api.views.DependenciesAPIView` | `api-dependencies` |

## groups

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/groups/` | GET, POST | `accounts.api.views.GroupViewSet` | `group-list` |
| `/api/v1/groups/<pk>/` | DELETE, GET, PATCH, PUT | `accounts.api.views.GroupViewSet` | `group-detail` |
| `/api/v1/groups/<pk>/permissions/` | GET, POST | `accounts.api.views.GroupViewSet` | `group-permissions` |
| `/api/v1/groups/<pk>/users/` | GET, POST | `accounts.api.views.GroupViewSet` | `group-users` |

## incidents

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/incidents/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/incidents/custody-events/` | GET, POST | `incidents.api.views.EvidenceCustodyEventViewSet` | `evidencecustodyevent-list` |
| `/api/v1/incidents/custody-events/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.EvidenceCustodyEventViewSet` | `evidencecustodyevent-detail` |
| `/api/v1/incidents/custody-events/<pk>/history/` | GET | `incidents.api.views.EvidenceCustodyEventViewSet` | `evidencecustodyevent-history` |
| `/api/v1/incidents/custody-events/batch/` | POST | `incidents.api.views.EvidenceCustodyEventViewSet` | `evidencecustodyevent-batch-create` |
| `/api/v1/incidents/evidence/` | GET, POST | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-list` |
| `/api/v1/incidents/evidence/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-detail` |
| `/api/v1/incidents/evidence/<pk>/download/` | GET | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-download` |
| `/api/v1/incidents/evidence/<pk>/history/` | GET | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-history` |
| `/api/v1/incidents/evidence/<pk>/transition/` | GET, POST | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-transition` |
| `/api/v1/incidents/evidence/<pk>/verify-integrity/` | POST | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-verify-integrity` |
| `/api/v1/incidents/evidence/batch/` | POST | `incidents.api.views.IncidentEvidenceViewSet` | `incidentevidence-batch-create` |
| `/api/v1/incidents/incidents/` | GET, POST | `incidents.api.views.IncidentViewSet` | `incident-list` |
| `/api/v1/incidents/incidents/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentViewSet` | `incident-detail` |
| `/api/v1/incidents/incidents/<pk>/history/` | GET | `incidents.api.views.IncidentViewSet` | `incident-history` |
| `/api/v1/incidents/incidents/<pk>/transition/` | GET, POST | `incidents.api.views.IncidentViewSet` | `incident-transition` |
| `/api/v1/incidents/incidents/batch/` | POST | `incidents.api.views.IncidentViewSet` | `incident-batch-create` |
| `/api/v1/incidents/notification-filings/` | GET, POST | `incidents.api.views.NotificationFilingViewSet` | `notificationfiling-list` |
| `/api/v1/incidents/notification-filings/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.NotificationFilingViewSet` | `notificationfiling-detail` |
| `/api/v1/incidents/notification-filings/<pk>/history/` | GET | `incidents.api.views.NotificationFilingViewSet` | `notificationfiling-history` |
| `/api/v1/incidents/notification-filings/<pk>/proof/` | GET | `incidents.api.views.NotificationFilingViewSet` | `notificationfiling-proof` |
| `/api/v1/incidents/notification-filings/batch/` | POST | `incidents.api.views.NotificationFilingViewSet` | `notificationfiling-batch-create` |
| `/api/v1/incidents/notifications/` | GET, POST | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-list` |
| `/api/v1/incidents/notifications/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-detail` |
| `/api/v1/incidents/notifications/<pk>/history/` | GET | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-history` |
| `/api/v1/incidents/notifications/<pk>/proof/` | GET | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-proof` |
| `/api/v1/incidents/notifications/<pk>/transition/` | GET, POST | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-transition` |
| `/api/v1/incidents/notifications/batch/` | POST | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-batch-create` |
| `/api/v1/incidents/notifications/overdue/` | GET | `incidents.api.views.IncidentNotificationViewSet` | `incidentnotification-overdue` |
| `/api/v1/incidents/obligation-templates/` | GET, POST | `incidents.api.views.ReportingObligationTemplateViewSet` | `reportingobligationtemplate-list` |
| `/api/v1/incidents/obligation-templates/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.ReportingObligationTemplateViewSet` | `reportingobligationtemplate-detail` |
| `/api/v1/incidents/obligation-templates/<pk>/history/` | GET | `incidents.api.views.ReportingObligationTemplateViewSet` | `reportingobligationtemplate-history` |
| `/api/v1/incidents/obligation-templates/<pk>/transition/` | GET, POST | `incidents.api.views.ReportingObligationTemplateViewSet` | `reportingobligationtemplate-transition` |
| `/api/v1/incidents/obligation-templates/batch/` | POST | `incidents.api.views.ReportingObligationTemplateViewSet` | `reportingobligationtemplate-batch-create` |
| `/api/v1/incidents/personal-data-breaches/` | GET, POST | `incidents.api.views.PersonalDataBreachViewSet` | `personaldatabreach-list` |
| `/api/v1/incidents/personal-data-breaches/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.PersonalDataBreachViewSet` | `personaldatabreach-detail` |
| `/api/v1/incidents/personal-data-breaches/<pk>/history/` | GET | `incidents.api.views.PersonalDataBreachViewSet` | `personaldatabreach-history` |
| `/api/v1/incidents/personal-data-breaches/<pk>/transition/` | GET, POST | `incidents.api.views.PersonalDataBreachViewSet` | `personaldatabreach-transition` |
| `/api/v1/incidents/personal-data-breaches/batch/` | POST | `incidents.api.views.PersonalDataBreachViewSet` | `personaldatabreach-batch-create` |
| `/api/v1/incidents/post-incident-reviews/` | GET, POST | `incidents.api.views.PostIncidentReviewViewSet` | `postincidentreview-list` |
| `/api/v1/incidents/post-incident-reviews/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.PostIncidentReviewViewSet` | `postincidentreview-detail` |
| `/api/v1/incidents/post-incident-reviews/<pk>/history/` | GET | `incidents.api.views.PostIncidentReviewViewSet` | `postincidentreview-history` |
| `/api/v1/incidents/post-incident-reviews/<pk>/transition/` | GET, POST | `incidents.api.views.PostIncidentReviewViewSet` | `postincidentreview-transition` |
| `/api/v1/incidents/post-incident-reviews/batch/` | POST | `incidents.api.views.PostIncidentReviewViewSet` | `postincidentreview-batch-create` |
| `/api/v1/incidents/reporting-authorities/` | GET, POST | `incidents.api.views.ReportingAuthorityViewSet` | `reportingauthority-list` |
| `/api/v1/incidents/reporting-authorities/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.ReportingAuthorityViewSet` | `reportingauthority-detail` |
| `/api/v1/incidents/reporting-authorities/<pk>/history/` | GET | `incidents.api.views.ReportingAuthorityViewSet` | `reportingauthority-history` |
| `/api/v1/incidents/reporting-authorities/<pk>/transition/` | GET, POST | `incidents.api.views.ReportingAuthorityViewSet` | `reportingauthority-transition` |
| `/api/v1/incidents/reporting-authorities/batch/` | POST | `incidents.api.views.ReportingAuthorityViewSet` | `reportingauthority-batch-create` |
| `/api/v1/incidents/response-actions/` | GET, POST | `incidents.api.views.IncidentResponseActionViewSet` | `incidentresponseaction-list` |
| `/api/v1/incidents/response-actions/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentResponseActionViewSet` | `incidentresponseaction-detail` |
| `/api/v1/incidents/response-actions/<pk>/history/` | GET | `incidents.api.views.IncidentResponseActionViewSet` | `incidentresponseaction-history` |
| `/api/v1/incidents/response-actions/batch/` | POST | `incidents.api.views.IncidentResponseActionViewSet` | `incidentresponseaction-batch-create` |
| `/api/v1/incidents/response-plans/` | GET, POST | `incidents.api.views.IncidentResponsePlanViewSet` | `incidentresponseplan-list` |
| `/api/v1/incidents/response-plans/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentResponsePlanViewSet` | `incidentresponseplan-detail` |
| `/api/v1/incidents/response-plans/<pk>/history/` | GET | `incidents.api.views.IncidentResponsePlanViewSet` | `incidentresponseplan-history` |
| `/api/v1/incidents/response-plans/<pk>/transition/` | GET, POST | `incidents.api.views.IncidentResponsePlanViewSet` | `incidentresponseplan-transition` |
| `/api/v1/incidents/response-plans/batch/` | POST | `incidents.api.views.IncidentResponsePlanViewSet` | `incidentresponseplan-batch-create` |
| `/api/v1/incidents/security-events/` | GET, POST | `incidents.api.views.SecurityEventViewSet` | `securityevent-list` |
| `/api/v1/incidents/security-events/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.SecurityEventViewSet` | `securityevent-detail` |
| `/api/v1/incidents/security-events/<pk>/history/` | GET | `incidents.api.views.SecurityEventViewSet` | `securityevent-history` |
| `/api/v1/incidents/security-events/<pk>/promote/` | POST | `incidents.api.views.SecurityEventViewSet` | `securityevent-promote` |
| `/api/v1/incidents/security-events/<pk>/transition/` | GET, POST | `incidents.api.views.SecurityEventViewSet` | `securityevent-transition` |
| `/api/v1/incidents/security-events/batch/` | POST | `incidents.api.views.SecurityEventViewSet` | `securityevent-batch-create` |
| `/api/v1/incidents/timeline-entries/` | GET, POST | `incidents.api.views.IncidentTimelineEntryViewSet` | `incidenttimelineentry-list` |
| `/api/v1/incidents/timeline-entries/<pk>/` | DELETE, GET, PATCH, PUT | `incidents.api.views.IncidentTimelineEntryViewSet` | `incidenttimelineentry-detail` |
| `/api/v1/incidents/timeline-entries/<pk>/history/` | GET | `incidents.api.views.IncidentTimelineEntryViewSet` | `incidenttimelineentry-history` |
| `/api/v1/incidents/timeline-entries/batch/` | POST | `incidents.api.views.IncidentTimelineEntryViewSet` | `incidenttimelineentry-batch-create` |

## mcp

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/mcp/.well-known/oauth-protected-resource` | - | `mcp.api.views_mcp.mcp_metadata_view` | `mcp-metadata` |

## notifications

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/notifications/` | GET | `accounts.api.views.NotificationViewSet` | `notification-list` |
| `/api/v1/notifications/<pk>/` | GET | `accounts.api.views.NotificationViewSet` | `notification-detail` |
| `/api/v1/notifications/<pk>/mark_read/` | POST | `accounts.api.views.NotificationViewSet` | `notification-mark-read` |
| `/api/v1/notifications/mark_all_read/` | POST | `accounts.api.views.NotificationViewSet` | `notification-mark-all-read` |
| `/api/v1/notifications/unread_count/` | GET | `accounts.api.views.NotificationViewSet` | `notification-unread-count` |

## oauth

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/oauth/applications/` | GET, POST, OPTIONS | `mcp.api.views_oauth.OAuthApplicationListCreateView` | `oauth-applications` |
| `/api/v1/oauth/applications/<uuid:pk>/` | GET, DELETE, OPTIONS | `mcp.api.views_oauth.OAuthApplicationDetailView` | `oauth-application-detail` |
| `/api/v1/oauth/register/` | POST, OPTIONS | `mcp.api.views_oauth.OAuthRegisterView` | `oauth-register` |
| `/api/v1/oauth/token/` | POST, OPTIONS | `mcp.api.views_oauth.OAuthTokenView` | `oauth-token` |

## permissions

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/permissions/` | GET | `accounts.api.views.PermissionViewSet` | `permission-list` |
| `/api/v1/permissions/<pk>/` | GET | `accounts.api.views.PermissionViewSet` | `permission-detail` |
| `/api/v1/permissions/by_module/` | GET | `accounts.api.views.PermissionViewSet` | `permission-by-module` |

## reports

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/reports/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/reports/decisions/` | GET, POST | `reports.api.views.ManagementReviewDecisionViewSet` | `managementreviewdecision-list` |
| `/api/v1/reports/decisions/<pk>/` | DELETE, GET, PATCH, PUT | `reports.api.views.ManagementReviewDecisionViewSet` | `managementreviewdecision-detail` |
| `/api/v1/reports/decisions/<pk>/promote/` | POST | `reports.api.views.ManagementReviewDecisionViewSet` | `managementreviewdecision-promote` |
| `/api/v1/reports/isms-changes/` | GET, POST | `reports.api.views.IsmsChangeViewSet` | `ismschange-list` |
| `/api/v1/reports/isms-changes/<pk>/` | DELETE, GET, PATCH, PUT | `reports.api.views.IsmsChangeViewSet` | `ismschange-detail` |
| `/api/v1/reports/management-reviews/` | GET, POST | `reports.api.views.ManagementReviewViewSet` | `managementreview-list` |
| `/api/v1/reports/management-reviews/<pk>/` | DELETE, GET, PATCH, PUT | `reports.api.views.ManagementReviewViewSet` | `managementreview-detail` |
| `/api/v1/reports/management-reviews/<pk>/decisions/` | GET, POST | `reports.api.views.ManagementReviewViewSet` | `managementreview-decisions` |
| `/api/v1/reports/management-reviews/<pk>/export/` | GET | `reports.api.views.ManagementReviewViewSet` | `managementreview-export` |
| `/api/v1/reports/management-reviews/<pk>/isms-changes/` | GET, POST | `reports.api.views.ManagementReviewViewSet` | `managementreview-isms-changes` |
| `/api/v1/reports/management-reviews/<pk>/transition/` | POST | `reports.api.views.ManagementReviewViewSet` | `managementreview-transition` |
| `/api/v1/reports/reports/` | GET | `reports.api.views.ReportViewSet` | `report-list` |
| `/api/v1/reports/reports/<pk>/` | GET | `reports.api.views.ReportViewSet` | `report-detail` |
| `/api/v1/reports/reports/generate-audit-report/` | POST | `reports.api.views.ReportViewSet` | `report-generate-audit-report` |
| `/api/v1/reports/reports/generate-management-review/` | POST | `reports.api.views.ReportViewSet` | `report-generate-management-review` |
| `/api/v1/reports/reports/generate-soa/` | POST | `reports.api.views.ReportViewSet` | `report-generate-soa` |

## risks

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/risks/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/risks/acceptances/` | GET, POST | `risks.api.views.RiskAcceptanceViewSet` | `riskacceptance-list` |
| `/api/v1/risks/acceptances/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.RiskAcceptanceViewSet` | `riskacceptance-detail` |
| `/api/v1/risks/acceptances/<pk>/history/` | GET | `risks.api.views.RiskAcceptanceViewSet` | `riskacceptance-history` |
| `/api/v1/risks/acceptances/<pk>/transition/` | GET, POST | `risks.api.views.RiskAcceptanceViewSet` | `riskacceptance-transition` |
| `/api/v1/risks/acceptances/batch/` | POST | `risks.api.views.RiskAcceptanceViewSet` | `riskacceptance-batch-create` |
| `/api/v1/risks/assessments/` | GET, POST | `risks.api.views.RiskAssessmentViewSet` | `riskassessment-list` |
| `/api/v1/risks/assessments/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.RiskAssessmentViewSet` | `riskassessment-detail` |
| `/api/v1/risks/assessments/<pk>/history/` | GET | `risks.api.views.RiskAssessmentViewSet` | `riskassessment-history` |
| `/api/v1/risks/assessments/<pk>/transition/` | GET, POST | `risks.api.views.RiskAssessmentViewSet` | `riskassessment-transition` |
| `/api/v1/risks/criteria/` | GET, POST | `risks.api.views.RiskCriteriaViewSet` | `riskcriteria-list` |
| `/api/v1/risks/criteria/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.RiskCriteriaViewSet` | `riskcriteria-detail` |
| `/api/v1/risks/criteria/<pk>/history/` | GET | `risks.api.views.RiskCriteriaViewSet` | `riskcriteria-history` |
| `/api/v1/risks/ebios/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/risks/ebios/attack-path-steps/` | GET, POST | `risks.api.ebios.views.AttackPathStepViewSet` | `attackpathstep-list` |
| `/api/v1/risks/ebios/attack-path-steps/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.AttackPathStepViewSet` | `attackpathstep-detail` |
| `/api/v1/risks/ebios/attack-path-steps/<pk>/history/` | GET | `risks.api.ebios.views.AttackPathStepViewSet` | `attackpathstep-history` |
| `/api/v1/risks/ebios/attack-path-steps/batch/` | POST | `risks.api.ebios.views.AttackPathStepViewSet` | `attackpathstep-batch-create` |
| `/api/v1/risks/ebios/attack-techniques/` | GET, POST | `risks.api.ebios.views.AttackTechniqueViewSet` | `attacktechnique-list` |
| `/api/v1/risks/ebios/attack-techniques/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.AttackTechniqueViewSet` | `attacktechnique-detail` |
| `/api/v1/risks/ebios/attack-techniques/<pk>/history/` | GET | `risks.api.ebios.views.AttackTechniqueViewSet` | `attacktechnique-history` |
| `/api/v1/risks/ebios/attack-techniques/batch/` | POST | `risks.api.ebios.views.AttackTechniqueViewSet` | `attacktechnique-batch-create` |
| `/api/v1/risks/ebios/baseline-gaps/` | GET, POST | `risks.api.ebios.views.BaselineGapViewSet` | `baselinegap-list` |
| `/api/v1/risks/ebios/baseline-gaps/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.BaselineGapViewSet` | `baselinegap-detail` |
| `/api/v1/risks/ebios/baseline-gaps/<pk>/history/` | GET | `risks.api.ebios.views.BaselineGapViewSet` | `baselinegap-history` |
| `/api/v1/risks/ebios/baseline-gaps/batch/` | POST | `risks.api.ebios.views.BaselineGapViewSet` | `baselinegap-batch-create` |
| `/api/v1/risks/ebios/baselines/` | GET, POST | `risks.api.ebios.views.SecurityBaselineViewSet` | `securitybaseline-list` |
| `/api/v1/risks/ebios/baselines/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.SecurityBaselineViewSet` | `securitybaseline-detail` |
| `/api/v1/risks/ebios/baselines/<pk>/history/` | GET | `risks.api.ebios.views.SecurityBaselineViewSet` | `securitybaseline-history` |
| `/api/v1/risks/ebios/baselines/<pk>/transition/` | GET, POST | `risks.api.ebios.views.SecurityBaselineViewSet` | `securitybaseline-transition` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/` | GET, POST | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-list` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-detail` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/<pk>/history/` | GET | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-history` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/<pk>/transition/` | GET, POST | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-transition` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/batch/` | POST | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-batch-create` |
| `/api/v1/risks/ebios/ecosystem-stakeholders/graph/` | GET | `risks.api.ebios.views.EcosystemStakeholderViewSet` | `ecosystemstakeholder-graph` |
| `/api/v1/risks/ebios/feared-events/` | GET, POST | `risks.api.ebios.views.FearedEventViewSet` | `fearedevent-list` |
| `/api/v1/risks/ebios/feared-events/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.FearedEventViewSet` | `fearedevent-detail` |
| `/api/v1/risks/ebios/feared-events/<pk>/history/` | GET | `risks.api.ebios.views.FearedEventViewSet` | `fearedevent-history` |
| `/api/v1/risks/ebios/feared-events/batch/` | POST | `risks.api.ebios.views.FearedEventViewSet` | `fearedevent-batch-create` |
| `/api/v1/risks/ebios/mitre-techniques/` | GET | `risks.api.ebios.views.MitreAttackTechniqueViewSet` | `mitreattacktechnique-list` |
| `/api/v1/risks/ebios/mitre-techniques/<pk>/` | GET | `risks.api.ebios.views.MitreAttackTechniqueViewSet` | `mitreattacktechnique-detail` |
| `/api/v1/risks/ebios/operational-scenarios/` | GET, POST | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-list` |
| `/api/v1/risks/ebios/operational-scenarios/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-detail` |
| `/api/v1/risks/ebios/operational-scenarios/<pk>/consolidate/` | POST | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-consolidate` |
| `/api/v1/risks/ebios/operational-scenarios/<pk>/history/` | GET | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-history` |
| `/api/v1/risks/ebios/operational-scenarios/<pk>/transition/` | GET, POST | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-transition` |
| `/api/v1/risks/ebios/operational-scenarios/batch/` | POST | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-batch-create` |
| `/api/v1/risks/ebios/operational-scenarios/mitre-heatmap/` | GET | `risks.api.ebios.views.OperationalScenarioViewSet` | `operationalscenario-mitre-heatmap` |
| `/api/v1/risks/ebios/pacs-measures/` | GET, POST | `risks.api.ebios.views.PACSMeasureViewSet` | `pacsmeasure-list` |
| `/api/v1/risks/ebios/pacs-measures/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.PACSMeasureViewSet` | `pacsmeasure-detail` |
| `/api/v1/risks/ebios/pacs-measures/<pk>/history/` | GET | `risks.api.ebios.views.PACSMeasureViewSet` | `pacsmeasure-history` |
| `/api/v1/risks/ebios/pacs-measures/batch/` | POST | `risks.api.ebios.views.PACSMeasureViewSet` | `pacsmeasure-batch-create` |
| `/api/v1/risks/ebios/risk-sources/` | GET, POST | `risks.api.ebios.views.RiskSourceViewSet` | `risksource-list` |
| `/api/v1/risks/ebios/risk-sources/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.RiskSourceViewSet` | `risksource-detail` |
| `/api/v1/risks/ebios/risk-sources/<pk>/history/` | GET | `risks.api.ebios.views.RiskSourceViewSet` | `risksource-history` |
| `/api/v1/risks/ebios/risk-sources/<pk>/transition/` | GET, POST | `risks.api.ebios.views.RiskSourceViewSet` | `risksource-transition` |
| `/api/v1/risks/ebios/risk-sources/batch/` | POST | `risks.api.ebios.views.RiskSourceViewSet` | `risksource-batch-create` |
| `/api/v1/risks/ebios/sr-ov-pairs/` | GET, POST | `risks.api.ebios.views.RiskSourceObjectivePairViewSet` | `risksourceobjectivepair-list` |
| `/api/v1/risks/ebios/sr-ov-pairs/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.RiskSourceObjectivePairViewSet` | `risksourceobjectivepair-detail` |
| `/api/v1/risks/ebios/sr-ov-pairs/<pk>/history/` | GET | `risks.api.ebios.views.RiskSourceObjectivePairViewSet` | `risksourceobjectivepair-history` |
| `/api/v1/risks/ebios/sr-ov-pairs/<pk>/transition/` | GET, POST | `risks.api.ebios.views.RiskSourceObjectivePairViewSet` | `risksourceobjectivepair-transition` |
| `/api/v1/risks/ebios/sr-ov-pairs/batch/` | POST | `risks.api.ebios.views.RiskSourceObjectivePairViewSet` | `risksourceobjectivepair-batch-create` |
| `/api/v1/risks/ebios/strategic-scenarios/` | GET, POST | `risks.api.ebios.views.StrategicScenarioViewSet` | `strategicscenario-list` |
| `/api/v1/risks/ebios/strategic-scenarios/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.StrategicScenarioViewSet` | `strategicscenario-detail` |
| `/api/v1/risks/ebios/strategic-scenarios/<pk>/history/` | GET | `risks.api.ebios.views.StrategicScenarioViewSet` | `strategicscenario-history` |
| `/api/v1/risks/ebios/strategic-scenarios/<pk>/transition/` | GET, POST | `risks.api.ebios.views.StrategicScenarioViewSet` | `strategicscenario-transition` |
| `/api/v1/risks/ebios/strategic-scenarios/batch/` | POST | `risks.api.ebios.views.StrategicScenarioViewSet` | `strategicscenario-batch-create` |
| `/api/v1/risks/ebios/study-frameworks/` | GET, POST | `risks.api.ebios.views.StudyFrameworkViewSet` | `studyframework-list` |
| `/api/v1/risks/ebios/study-frameworks/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.StudyFrameworkViewSet` | `studyframework-detail` |
| `/api/v1/risks/ebios/study-frameworks/<pk>/history/` | GET | `risks.api.ebios.views.StudyFrameworkViewSet` | `studyframework-history` |
| `/api/v1/risks/ebios/summaries/` | GET, POST | `risks.api.ebios.views.EbiosSummaryViewSet` | `ebiossummary-list` |
| `/api/v1/risks/ebios/summaries/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.EbiosSummaryViewSet` | `ebiossummary-detail` |
| `/api/v1/risks/ebios/summaries/<pk>/capture-mappings/` | POST | `risks.api.ebios.views.EbiosSummaryViewSet` | `ebiossummary-capture-mappings` |
| `/api/v1/risks/ebios/summaries/<pk>/history/` | GET | `risks.api.ebios.views.EbiosSummaryViewSet` | `ebiossummary-history` |
| `/api/v1/risks/ebios/summaries/<pk>/transition/` | GET, POST | `risks.api.ebios.views.EbiosSummaryViewSet` | `ebiossummary-transition` |
| `/api/v1/risks/ebios/targeted-objectives/` | GET, POST | `risks.api.ebios.views.TargetedObjectiveViewSet` | `targetedobjective-list` |
| `/api/v1/risks/ebios/targeted-objectives/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.TargetedObjectiveViewSet` | `targetedobjective-detail` |
| `/api/v1/risks/ebios/targeted-objectives/<pk>/history/` | GET | `risks.api.ebios.views.TargetedObjectiveViewSet` | `targetedobjective-history` |
| `/api/v1/risks/ebios/targeted-objectives/batch/` | POST | `risks.api.ebios.views.TargetedObjectiveViewSet` | `targetedobjective-batch-create` |
| `/api/v1/risks/ebios/workshops/` | GET, POST | `risks.api.ebios.views.EbiosWorkshopProgressViewSet` | `ebiosworkshopprogress-list` |
| `/api/v1/risks/ebios/workshops/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.ebios.views.EbiosWorkshopProgressViewSet` | `ebiosworkshopprogress-detail` |
| `/api/v1/risks/ebios/workshops/<pk>/history/` | GET | `risks.api.ebios.views.EbiosWorkshopProgressViewSet` | `ebiosworkshopprogress-history` |
| `/api/v1/risks/ebios/workshops/batch/` | POST | `risks.api.ebios.views.EbiosWorkshopProgressViewSet` | `ebiosworkshopprogress-batch-create` |
| `/api/v1/risks/iso27005-risks/` | GET, POST | `risks.api.views.ISO27005RiskViewSet` | `iso27005risk-list` |
| `/api/v1/risks/iso27005-risks/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.ISO27005RiskViewSet` | `iso27005risk-detail` |
| `/api/v1/risks/iso27005-risks/<pk>/history/` | GET | `risks.api.views.ISO27005RiskViewSet` | `iso27005risk-history` |
| `/api/v1/risks/iso27005-risks/<pk>/transition/` | GET, POST | `risks.api.views.ISO27005RiskViewSet` | `iso27005risk-transition` |
| `/api/v1/risks/iso27005-risks/batch/` | POST | `risks.api.views.ISO27005RiskViewSet` | `iso27005risk-batch-create` |
| `/api/v1/risks/risk-levels/` | GET | `risks.api.views.RiskLevelViewSet` | `risklevel-list` |
| `/api/v1/risks/risk-levels/<pk>/` | GET | `risks.api.views.RiskLevelViewSet` | `risklevel-detail` |
| `/api/v1/risks/risks/` | GET, POST | `risks.api.views.RiskViewSet` | `risk-list` |
| `/api/v1/risks/risks/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.RiskViewSet` | `risk-detail` |
| `/api/v1/risks/risks/<pk>/history/` | GET | `risks.api.views.RiskViewSet` | `risk-history` |
| `/api/v1/risks/risks/<pk>/transition/` | GET, POST | `risks.api.views.RiskViewSet` | `risk-transition` |
| `/api/v1/risks/risks/batch/` | POST | `risks.api.views.RiskViewSet` | `risk-batch-create` |
| `/api/v1/risks/scale-levels/` | GET | `risks.api.views.ScaleLevelViewSet` | `scalelevel-list` |
| `/api/v1/risks/scale-levels/<pk>/` | GET | `risks.api.views.ScaleLevelViewSet` | `scalelevel-detail` |
| `/api/v1/risks/threats/` | GET, POST | `risks.api.views.ThreatViewSet` | `threat-list` |
| `/api/v1/risks/threats/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.ThreatViewSet` | `threat-detail` |
| `/api/v1/risks/threats/<pk>/history/` | GET | `risks.api.views.ThreatViewSet` | `threat-history` |
| `/api/v1/risks/threats/<pk>/transition/` | GET, POST | `risks.api.views.ThreatViewSet` | `threat-transition` |
| `/api/v1/risks/threats/batch/` | POST | `risks.api.views.ThreatViewSet` | `threat-batch-create` |
| `/api/v1/risks/treatment-actions/` | GET, POST | `risks.api.views.TreatmentActionViewSet` | `treatmentaction-list` |
| `/api/v1/risks/treatment-actions/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.TreatmentActionViewSet` | `treatmentaction-detail` |
| `/api/v1/risks/treatment-plans/` | GET, POST | `risks.api.views.RiskTreatmentPlanViewSet` | `risktreatmentplan-list` |
| `/api/v1/risks/treatment-plans/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.RiskTreatmentPlanViewSet` | `risktreatmentplan-detail` |
| `/api/v1/risks/treatment-plans/<pk>/history/` | GET | `risks.api.views.RiskTreatmentPlanViewSet` | `risktreatmentplan-history` |
| `/api/v1/risks/treatment-plans/<pk>/transition/` | GET, POST | `risks.api.views.RiskTreatmentPlanViewSet` | `risktreatmentplan-transition` |
| `/api/v1/risks/treatment-plans/batch/` | POST | `risks.api.views.RiskTreatmentPlanViewSet` | `risktreatmentplan-batch-create` |
| `/api/v1/risks/vulnerabilities/` | GET, POST | `risks.api.views.VulnerabilityViewSet` | `vulnerability-list` |
| `/api/v1/risks/vulnerabilities/<pk>/` | DELETE, GET, PATCH, PUT | `risks.api.views.VulnerabilityViewSet` | `vulnerability-detail` |
| `/api/v1/risks/vulnerabilities/<pk>/history/` | GET | `risks.api.views.VulnerabilityViewSet` | `vulnerability-history` |
| `/api/v1/risks/vulnerabilities/<pk>/transition/` | GET, POST | `risks.api.views.VulnerabilityViewSet` | `vulnerability-transition` |
| `/api/v1/risks/vulnerabilities/batch/` | POST | `risks.api.views.VulnerabilityViewSet` | `vulnerability-batch-create` |

## root

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/mcp` | GET, POST, DELETE, OPTIONS | `mcp.api.views_mcp.McpEndpointView` | `mcp-endpoint` |

## saved-filters

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/saved-filters/` | GET, POST | `accounts.api.views.SavedFilterViewSet` | `saved-filter-list` |
| `/api/v1/saved-filters/<pk>/` | DELETE, GET, PATCH, PUT | `accounts.api.views.SavedFilterViewSet` | `saved-filter-detail` |

## trust-center

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/trust-center/` | GET, OPTIONS | `rest_framework.routers.APIRootView` | `api-root` |
| `/api/v1/trust-center/certifications/` | GET, POST | `trust_center.api.views.CertificationViewSet` | `trustcentercertification-list` |
| `/api/v1/trust-center/certifications/<pk>/` | DELETE, GET, PATCH, PUT | `trust_center.api.views.CertificationViewSet` | `trustcentercertification-detail` |
| `/api/v1/trust-center/certifications/<pk>/transition/` | POST | `trust_center.api.views.CertificationViewSet` | `trustcentercertification-transition` |
| `/api/v1/trust-center/documents/` | GET, POST | `trust_center.api.views.DocumentViewSet` | `trustcenterdocument-list` |
| `/api/v1/trust-center/documents/<pk>/` | DELETE, GET, PATCH, PUT | `trust_center.api.views.DocumentViewSet` | `trustcenterdocument-detail` |
| `/api/v1/trust-center/documents/<pk>/transition/` | POST | `trust_center.api.views.DocumentViewSet` | `trustcenterdocument-transition` |
| `/api/v1/trust-center/measures/` | GET, POST | `trust_center.api.views.MeasureViewSet` | `trustcentermeasure-list` |
| `/api/v1/trust-center/measures/<pk>/` | DELETE, GET, PATCH, PUT | `trust_center.api.views.MeasureViewSet` | `trustcentermeasure-detail` |
| `/api/v1/trust-center/measures/<pk>/transition/` | POST | `trust_center.api.views.MeasureViewSet` | `trustcentermeasure-transition` |
| `/api/v1/trust-center/settings/` | GET, PUT, OPTIONS | `trust_center.api.views.TrustCenterSettingsView` | `settings` |
| `/api/v1/trust-center/subprocessors/` | GET, POST | `trust_center.api.views.SubprocessorViewSet` | `trustcentersubprocessor-list` |
| `/api/v1/trust-center/subprocessors/<pk>/` | DELETE, GET, PATCH, PUT | `trust_center.api.views.SubprocessorViewSet` | `trustcentersubprocessor-detail` |
| `/api/v1/trust-center/subprocessors/<pk>/transition/` | POST | `trust_center.api.views.SubprocessorViewSet` | `trustcentersubprocessor-transition` |

## users

| Path | Methods | View | URL name |
| --- | --- | --- | --- |
| `/api/v1/users/` | GET, POST | `accounts.api.views.UserViewSet` | `user-list` |
| `/api/v1/users/<pk>/` | DELETE, GET, PATCH, PUT | `accounts.api.views.UserViewSet` | `user-detail` |
| `/api/v1/users/<pk>/groups/` | GET | `accounts.api.views.UserViewSet` | `user-groups` |
| `/api/v1/users/<pk>/permissions/` | GET | `accounts.api.views.UserViewSet` | `user-permissions` |
| `/api/v1/users/invite/` | POST | `accounts.api.views.UserViewSet` | `user-invite` |

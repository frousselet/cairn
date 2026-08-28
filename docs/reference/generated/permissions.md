<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from `accounts/constants.py` (`PERMISSION_REGISTRY`, `SYSTEM_GROUPS`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Permissions

Cairn does not use Django's per-model `add`/`change`/`delete` permissions. It declares its own flat codenames shaped `module.feature.action`, and every web view, REST endpoint and MCP tool is gated on one of them.

There are **311 permissions** across **8 modules**. They are created by a data migration from the registry below, so adding an entry there and migrating is the whole of adding a permission.

## Actions

| Action | Label | Meaning |
| --- | --- | --- |
| `create` | Create | Create a new record |
| `read` | Read | List and view records |
| `update` | Update | Edit an existing record |
| `delete` | Delete | Delete a record (only from a deletable lifecycle step) |
| `access` | Access | Reach a surface that is not a record (a page, a console) |
| `approve` | Approve | Perform a lifecycle transition that carries `permission_action="approve"` |

## Governance (`context`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `scope` | Scopes | `context.scope.create`, `context.scope.read`, `context.scope.update`, `context.scope.delete`, `context.scope.approve` |
| `issue` | Issues | `context.issue.create`, `context.issue.read`, `context.issue.update`, `context.issue.delete`, `context.issue.approve` |
| `stakeholder` | Stakeholders | `context.stakeholder.create`, `context.stakeholder.read`, `context.stakeholder.update`, `context.stakeholder.delete`, `context.stakeholder.approve` |
| `expectation` | Expectations | `context.expectation.create`, `context.expectation.read`, `context.expectation.update`, `context.expectation.delete` |
| `objective` | Objectives | `context.objective.create`, `context.objective.read`, `context.objective.update`, `context.objective.delete`, `context.objective.approve` |
| `swot` | SWOT analyses | `context.swot.create`, `context.swot.read`, `context.swot.update`, `context.swot.delete`, `context.swot.approve` |
| `role` | Roles | `context.role.create`, `context.role.read`, `context.role.update`, `context.role.delete`, `context.role.approve` |
| `role_assign` | Role assignment | `context.role_assign.update` |
| `activity` | Activities | `context.activity.create`, `context.activity.read`, `context.activity.update`, `context.activity.delete`, `context.activity.approve` |
| `indicator` | Indicators | `context.indicator.create`, `context.indicator.read`, `context.indicator.update`, `context.indicator.delete`, `context.indicator.approve` |
| `stakeholder_feedback` | Stakeholder feedback | `context.stakeholder_feedback.create`, `context.stakeholder_feedback.read`, `context.stakeholder_feedback.update`, `context.stakeholder_feedback.delete` |
| `site` | Sites | `context.site.create`, `context.site.read`, `context.site.update`, `context.site.delete`, `context.site.approve` |
| `config` | Context configuration | `context.config.read`, `context.config.update` |
| `export` | Context export | `context.export.read` |
| `audit_trail` | Context audit trail | `context.audit_trail.read` |

## Assets (`assets`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `essential_asset` | Essential assets | `assets.essential_asset.create`, `assets.essential_asset.read`, `assets.essential_asset.update`, `assets.essential_asset.delete`, `assets.essential_asset.approve` |
| `essential_asset_evaluate` | Essential asset evaluation | `assets.essential_asset_evaluate.update` |
| `support_asset` | Support assets | `assets.support_asset.create`, `assets.support_asset.read`, `assets.support_asset.update`, `assets.support_asset.delete`, `assets.support_asset.approve` |
| `dependency` | Dependencies | `assets.dependency.create`, `assets.dependency.read`, `assets.dependency.update`, `assets.dependency.delete`, `assets.dependency.approve` |
| `group` | Asset groups | `assets.group.create`, `assets.group.read`, `assets.group.update`, `assets.group.delete`, `assets.group.approve` |
| `supplier` | Suppliers | `assets.supplier.create`, `assets.supplier.read`, `assets.supplier.update`, `assets.supplier.delete`, `assets.supplier.approve` |
| `supplier_dependency` | Supplier dependencies | `assets.supplier_dependency.create`, `assets.supplier_dependency.read`, `assets.supplier_dependency.update`, `assets.supplier_dependency.delete`, `assets.supplier_dependency.approve` |
| `contract` | Contracts | `assets.contract.create`, `assets.contract.read`, `assets.contract.update`, `assets.contract.delete`, `assets.contract.approve` |
| `certificate` | Certificates | `assets.certificate.create`, `assets.certificate.read`, `assets.certificate.update`, `assets.certificate.delete`, `assets.certificate.approve` |
| `import` | Asset import | `assets.import.create` |
| `config` | Asset configuration | `assets.config.create`, `assets.config.read`, `assets.config.update`, `assets.config.delete` |
| `export` | Asset export | `assets.export.read` |
| `audit_trail` | Asset audit trail | `assets.audit_trail.read` |

## Compliance (`compliance`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `framework` | Frameworks | `compliance.framework.create`, `compliance.framework.read`, `compliance.framework.update`, `compliance.framework.delete`, `compliance.framework.approve` |
| `section` | Sections | `compliance.section.create`, `compliance.section.read`, `compliance.section.update`, `compliance.section.delete` |
| `requirement` | Requirements | `compliance.requirement.create`, `compliance.requirement.read`, `compliance.requirement.update`, `compliance.requirement.delete`, `compliance.requirement.approve`, `compliance.requirement.assess` |
| `assessment` | Compliance assessments | `compliance.assessment.create`, `compliance.assessment.read`, `compliance.assessment.update`, `compliance.assessment.delete`, `compliance.assessment.approve`, `compliance.assessment.validate` |
| `finding` | Nonconformities | `compliance.finding.create`, `compliance.finding.read`, `compliance.finding.update`, `compliance.finding.delete`, `compliance.finding.validate` |
| `mapping` | Inter-framework mappings | `compliance.mapping.create`, `compliance.mapping.read`, `compliance.mapping.update`, `compliance.mapping.delete` |
| `action_plan` | Action plans | `compliance.action_plan.create`, `compliance.action_plan.read`, `compliance.action_plan.update`, `compliance.action_plan.delete`, `compliance.action_plan.approve`, `compliance.action_plan.validate`, `compliance.action_plan.implement`, `compliance.action_plan.close`, `compliance.action_plan.cancel` |
| `config` | Compliance configuration | `compliance.config.read`, `compliance.config.update` |
| `export` | Compliance export | `compliance.export.read` |
| `audit_trail` | Compliance audit trail | `compliance.audit_trail.read` |

## Risk management (`risks`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `assessment` | Risk assessments | `risks.assessment.create`, `risks.assessment.read`, `risks.assessment.update`, `risks.assessment.delete`, `risks.assessment.approve` |
| `criteria` | Risk criteria | `risks.criteria.create`, `risks.criteria.read`, `risks.criteria.update`, `risks.criteria.delete` |
| `risk` | Risk register | `risks.risk.create`, `risks.risk.read`, `risks.risk.update`, `risks.risk.delete`, `risks.risk.approve` |
| `treatment` | Treatment plans | `risks.treatment.create`, `risks.treatment.read`, `risks.treatment.update`, `risks.treatment.delete`, `risks.treatment.approve` |
| `acceptance` | Risk acceptances | `risks.acceptance.create`, `risks.acceptance.read`, `risks.acceptance.update`, `risks.acceptance.delete`, `risks.acceptance.approve` |
| `threat` | Threats | `risks.threat.create`, `risks.threat.read`, `risks.threat.update`, `risks.threat.delete`, `risks.threat.approve` |
| `vulnerability` | Vulnerabilities | `risks.vulnerability.create`, `risks.vulnerability.read`, `risks.vulnerability.update`, `risks.vulnerability.delete`, `risks.vulnerability.approve` |
| `iso27005` | ISO 27005 analyses | `risks.iso27005.create`, `risks.iso27005.read`, `risks.iso27005.update`, `risks.iso27005.delete`, `risks.iso27005.approve` |
| `ebios_assessment` | EBIOS RM assessment pilotage | `risks.ebios_assessment.read`, `risks.ebios_assessment.update`, `risks.ebios_assessment.validate` |
| `ebios_baseline` | EBIOS RM security baseline (workshop 1) | `risks.ebios_baseline.create`, `risks.ebios_baseline.read`, `risks.ebios_baseline.update`, `risks.ebios_baseline.delete`, `risks.ebios_baseline.approve` |
| `ebios_risk_source` | EBIOS RM risk sources and objectives (workshop 2) | `risks.ebios_risk_source.create`, `risks.ebios_risk_source.read`, `risks.ebios_risk_source.update`, `risks.ebios_risk_source.delete`, `risks.ebios_risk_source.approve` |
| `ebios_ecosystem` | EBIOS RM ecosystem stakeholders (workshop 3) | `risks.ebios_ecosystem.create`, `risks.ebios_ecosystem.read`, `risks.ebios_ecosystem.update`, `risks.ebios_ecosystem.delete`, `risks.ebios_ecosystem.approve` |
| `ebios_strategic` | EBIOS RM strategic scenarios (workshop 3) | `risks.ebios_strategic.create`, `risks.ebios_strategic.read`, `risks.ebios_strategic.update`, `risks.ebios_strategic.delete`, `risks.ebios_strategic.approve` |
| `ebios_operational` | EBIOS RM operational scenarios (workshop 4) | `risks.ebios_operational.create`, `risks.ebios_operational.read`, `risks.ebios_operational.update`, `risks.ebios_operational.delete`, `risks.ebios_operational.approve` |
| `ebios_summary` | EBIOS RM summary and PACS (workshop 5) | `risks.ebios_summary.create`, `risks.ebios_summary.read`, `risks.ebios_summary.update`, `risks.ebios_summary.delete`, `risks.ebios_summary.approve` |
| `export` | Risk export | `risks.export.read` |
| `audit_trail` | Risk audit trail | `risks.audit_trail.read` |

## Incidents (`incidents`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `incident` | Security incidents | `incidents.incident.create`, `incidents.incident.read`, `incidents.incident.update`, `incidents.incident.delete`, `incidents.incident.validate` |
| `event` | Security events | `incidents.event.create`, `incidents.event.read`, `incidents.event.update`, `incidents.event.delete`, `incidents.event.validate` |
| `response_plan` | Incident response plans | `incidents.response_plan.create`, `incidents.response_plan.read`, `incidents.response_plan.update`, `incidents.response_plan.delete`, `incidents.response_plan.approve` |
| `evidence` | Incident evidence | `incidents.evidence.create`, `incidents.evidence.read`, `incidents.evidence.update`, `incidents.evidence.delete`, `incidents.evidence.approve` |
| `notification` | Incident notifications | `incidents.notification.create`, `incidents.notification.read`, `incidents.notification.update`, `incidents.notification.delete`, `incidents.notification.approve` |
| `review` | Post-incident reviews | `incidents.review.create`, `incidents.review.read`, `incidents.review.update`, `incidents.review.delete`, `incidents.review.validate` |

## Reports (`reports`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `report` | Reports | `reports.report.create`, `reports.report.read`, `reports.report.delete` |
| `management_review` | Management reviews | `reports.management_review.create`, `reports.management_review.read`, `reports.management_review.update`, `reports.management_review.delete`, `reports.management_review.approve` |

## Trust Center (`trust_center`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `settings` | Settings | `trust_center.settings.read`, `trust_center.settings.update` |
| `certification` | Certifications | `trust_center.certification.create`, `trust_center.certification.read`, `trust_center.certification.update`, `trust_center.certification.delete`, `trust_center.certification.approve` |
| `subprocessor` | Subprocessors | `trust_center.subprocessor.create`, `trust_center.subprocessor.read`, `trust_center.subprocessor.update`, `trust_center.subprocessor.delete`, `trust_center.subprocessor.approve` |
| `measure` | Measures | `trust_center.measure.create`, `trust_center.measure.read`, `trust_center.measure.update`, `trust_center.measure.delete`, `trust_center.measure.approve` |
| `document` | Documents | `trust_center.document.create`, `trust_center.document.read`, `trust_center.document.update`, `trust_center.document.delete`, `trust_center.document.approve` |
| `document_request` | Document requests | `trust_center.document_request.read`, `trust_center.document_request.approve`, `trust_center.document_request.delete` |

## System (`system`)

| Feature | Label | Codenames |
| --- | --- | --- |
| `admin_django` | Django administration | `system.admin_django.access` |
| `users` | Users | `system.users.create`, `system.users.read`, `system.users.update`, `system.users.delete`, `system.users.impersonate` |
| `groups` | Groups | `system.groups.create`, `system.groups.read`, `system.groups.update`, `system.groups.delete` |
| `audit_trail` | System audit trail | `system.audit_trail.read` |
| `assistant_feedback` | AI assistant feedback | `system.assistant_feedback.read` |
| `data_import` | Bulk data import | `system.data_import.override_dates` |
| `config` | System configuration | `system.config.read`, `system.config.update` |
| `webhooks` | Webhooks | `system.webhooks.create`, `system.webhooks.read`, `system.webhooks.update`, `system.webhooks.delete` |
| `notifications` | Notifications | `system.notifications.read`, `system.notifications.update` |
| `mcp` | MCP server | `system.mcp.access` |
| `oauth` | OAuth credentials | `system.oauth.create`, `system.oauth.read`, `system.oauth.delete` |

## System groups

Six groups ship with the platform and are kept in sync by the same data migration. A group's permission set is a filter over the codenames above, so a newly declared permission lands in the right groups automatically.

| Group | Permissions | Description |
| --- | --- | --- |
| Super Administrateur | 311 | Full technical administration of the platform. All permissions. |
| Administrateur | 310 | Full functional administration. All permissions except Django admin access. |
| RSSI / DPO | 247 | GRC system steering. Read, create, update, approve. No deletion or system configuration. |
| Auditeur | 74 | Platform consultation and audit. Read-only access to all modules. |
| Contributeur | 179 | GRC content contribution. Read, create, update. No deletion or system access. |
| Lecteur | 66 | Read-only access. Read on all modules except system. |

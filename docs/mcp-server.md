# MCP Server (Model Context Protocol)

Cairn ships with a built-in JSON-RPC 2.0 MCP server exposing 734 tools across all modules, so AI assistants and external clients can read and manage GRC data directly. Authentication uses OAuth 2.0. All tools enforce RBAC permissions and scope-based tenancy.

## Endpoints

| Endpoint | Purpose |
| -------- | ------- |
| `POST /api/v1/mcp` | JSON-RPC 2.0 MCP endpoint |
| `GET /api/v1/mcp/.well-known/oauth-protected-resource` | OAuth resource metadata (RFC 9728) for client discovery |
| `POST /api/v1/oauth/register/` | Dynamic client registration |
| `POST /api/v1/oauth/token/` | Token endpoint (authorization code + refresh token grants) |

## CRUD pattern

Most domain entities expose a standard set of operations generated automatically:

| Operation | Tool name pattern | Description |
| --------- | ----------------- | ----------- |
| List | `list_{entity}s` | Paginated list with search, filters, limit/offset |
| Get | `get_{entity}` | Get a single object by UUID |
| Create | `create_{entity}` | Create a new object |
| Batch Create / Upsert | `batch_create_{entity}s` | Create or upsert up to 500 objects with partial success (non-atomic). Pass `match_on` (a list of field names) to update matching records instead of duplicating, making a re-run idempotent |
| Update | `update_{entity}` | Update an existing object |
| Delete | `delete_{entity}` | Delete an object (only allowed from a deletable lifecycle state) |
| Transition | `transition_{entity}` | Change the object's lifecycle state (draft / pending / validated / archived), validating permissions, mandatory comments and side effects |
| Allowed transitions | `{entity}_allowed_transitions` | List the lifecycle transitions the caller may perform from the current state |
| History | `get_{entity}_history` | Unified change timeline (field diffs, approvals and lifecycle transitions), with `limit` / `offset` pagination |
| Approve | `approve_{entity}` | Deprecated alias of `transition_{entity}` with `target_state="validated"` |

## Context module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `scope` | Yes | type, status |
| `issue` | Yes | type, category |
| `stakeholder` | Yes | type, influence_level |
| `objective` | Yes | type, status |
| `role` | Yes | - |
| `activity` | Yes | type, criticality |
| `site` | Yes | type, status |
| `indicator` | Yes | indicator_type, status, format, collection_method |
| `indicator_measurement` | No | indicator_id |
| `responsibility` | No | role_id, raci_type |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `list_tags` | List all tags |
| `create_tag` | Create a tag |
| `delete_tag` | Delete a tag |

## Assets module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `essential_asset` | Yes | type, category, status |
| `support_asset` | Yes | type, category, status |
| `asset_dependency` | Yes | essential_asset_id, support_asset_id, dependency_type, criticality |
| `site_asset_dependency` | Yes | support_asset_id, site_id, dependency_type, criticality |
| `site_supplier_dependency` | Yes | site_id, supplier_id, dependency_type, criticality |
| `asset_group` | Yes | type, status |
| `supplier` | Yes | type, criticality, status |
| `supplier_dependency` | Yes | support_asset_id, supplier_id |
| `contract` | Yes | status (parties via scope_ids/supplier_ids/client_ids; PDF upload is web-only) |
| `asset_valuation` | No | essential_asset_id |
| `supplier_type` | No | - |
| `supplier_type_requirement` | No | supplier_type_id |
| `supplier_requirement` | No | supplier_id, compliance_status |
| `supplier_requirement_review` | No | supplier_requirement_id, result |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `update_supplier_logo` | Upload a logo via base64 data URI or public URL with automatic variant generation (128/64/32/16px) |

## Compliance module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `framework` | Yes | type, category, status |
| `section` | No | framework_id, parent_section_id |
| `requirement` | Yes | framework_id, section_id, compliance_status, type, priority |
| `compliance_assessment` | Yes | status |
| `assessment_result` | No | assessment_id, requirement_id, compliance_status |
| `requirement_mapping` | No | source_requirement_id, target_requirement_id, mapping_type |
| `action_plan` | Yes | status, priority |
| `finding` | No | assessment_id, finding_type, source, effectiveness_verdict |

> **Permission change.** `list_findings`, `get_finding`, `create_finding`, `update_finding` and `delete_finding` are gated by `compliance.finding.*` instead of `compliance.assessment.*`. Findings are now the organisation-wide nonconformity register rather than a child of an audit, so they carry their own feature. The upgrade migration grants `compliance.finding.<action>` to every group already holding `compliance.assessment.<action>`, so existing integrations keep working; a group created afterwards needs the new codenames explicitly. These tools are also scope-filtered now, where they previously returned every row on the instance.

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `get_framework_compliance_summary` | Compliance summary with section-level scores and status distribution |
| `action_plan_transition` | Transition an action plan through the Kanban workflow (forward, refusal, cancellation) |
| `action_plan_transitions` | List transition history for an action plan (legacy; `get_action_plan_history` is the canonical superset) |
| `action_plan_kanban` | Get action plans grouped by status for Kanban board with workflow rules |
| `action_plan_allowed_transitions` | Get allowed transitions for an action plan with permission checks |
| `kanban_board` | Get the unified To do / Doing / Done board aggregating action plans, treatment actions, audits and risk assessments (read-only) |
| `list_action_plan_comments` | List threaded comments on an action plan |
| `create_action_plan_comment` | Create a comment or reply on an action plan |

## Risks module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `risk_assessment` | Yes | status |
| `risk_criteria` | No | status |
| `scale_level` | No | criteria_id, scale_type |
| `risk_level` | No | criteria_id, requires_treatment |
| `risk` | Yes | status, priority, assessment_id |
| `risk_treatment_plan` | Yes | status, risk_id |
| `treatment_action` | No | treatment_plan_id, status |
| `risk_acceptance` | No | risk_id, status |
| `threat` | Yes | type, status |
| `vulnerability` | Yes | category, severity, status |
| `iso27005_risk` | No | assessment_id, threat_id, vulnerability_id |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `list_risk_requirements` | List compliance requirements linked to a risk |
| `list_requirement_risks` | List risks linked to a compliance requirement |
| `link_risk_requirements` | Link requirements to a risk (additive) |
| `unlink_risk_requirements` | Remove requirement links from a risk |
| `set_risk_requirements` | Replace all linked requirements on a risk |

## Incidents module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `incident` | Yes | category, severity, detection_source, tlp, is_exercise, personal_data_involved, is_significant, workflow_state, incident_manager_id, response_plan_id, parent_incident_id |
| `security_event` | Yes | event_class, category, detection_source, is_anonymous, triage_decision, workflow_state, incident_id, reported_by_supplier_id |
| `incident_response_plan` | Yes | workflow_state, owner_id, approved_by_id |
| `incident_response_action` | No | incident_id, action_type, status, owner_id, performed_by_id, effectiveness |
| `incident_evidence` | Yes | incident_id, evidence_type, hash_algorithm, tlp, legal_hold, workflow_state, collected_by_id |
| `post_incident_review` | Yes | incident_id, root_cause_method, recurrence_likelihood, effectiveness_verdict, workflow_state, facilitator_id |
| `incident_notification` | Yes | incident_id, regime, recipient_kind, decision, channel, source, workflow_state, authority_id, template_id, no_fixed_deadline |
| `personal_data_breach` | Yes | incident_id, controller_role, article_34_exemption, high_risk_to_rights, special_categories, cross_border_eu, workflow_state |
| `reporting_authority` | Yes | authority_type, primary_regime, jurisdiction_country, workflow_state |
| `obligation_template` | Yes | regime, recipient_kind, authority_id, jurisdiction_country, min_severity, no_fixed_deadline, workflow_state |

The three ledgers below are **append-only**. They publish `list_*`, `get_*` and `get_*_history` and no `update_*` or `delete_*` at all : `save()` on an existing row and `delete()` both refuse on these models, so registering those tools would advertise an operation that can only ever fail. Their create tool is bespoke (see below) because the actor is forced to the calling account. `get_*_history` is the tamper-detection surface here : a row whose trail shows more writes than the design allows was altered outside the supported paths.

| Append-only ledger | Tools | Filters |
| ------------------ | ----- | ------- |
| `incident_timeline_entry` | `list_incident_timeline_entries`, `get_*`, `get_*_history` | incident_id, entry_type, source, is_evidence, author_id |
| `evidence_custody_event` | `list_evidence_custody_events`, `get_*`, `get_*_history` | evidence_id, action, source, integrity_ok, actor_id |
| `notification_filing` | `list_notification_filings`, `get_*`, `get_*_history` | notification_id, channel, outcome, is_correction, was_late, submitted_by_id |

> **Permissions.** The module is capped at six features : `incidents.incident`, `.event`, `.response_plan`, `.evidence`, `.notification` and `.review`. Child entities are gated by their parent's feature, so timeline and response-action tools consume `incidents.incident.*`, custody tools `incidents.evidence.*` and filing tools `incidents.notification.*`. Appending to a ledger is deliberately an `update` on the parent rather than a `create`. `reporting_authority` and `obligation_template` are the regulatory catalogue and are gated by `incidents.response_plan.*`, since the catalogue is part of the procedure.

> **Tool names are generated, plurals included.** The list and batch tools pluralise by appending `s` to the entity name, so the exact names are `list_incident_evidences`, `list_reporting_authoritys`, `list_personal_data_breachs` and `list_incident_timeline_entries`. Use them verbatim.

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `create_incident_timeline_entry` | Append one entry to an incident's chronology. The author is always the calling account and the source always `manual`. A mistake is corrected by appending a further entry of type `correction` naming the one it supersedes |
| `create_evidence_custody_event` | Record one handling act on an evidence item (collected, sealed, transferred, accessed, copied, analysed, released, returned, destroyed). The actor is always the calling account; a handover requires a named counterparty. The enum also accepts `integrity_verified`, but a verdict belongs to `verify_evidence_integrity`, which measures the artefact instead of taking the caller's word for it |
| `create_notification_filing` | Record that a notification obligation was actually transmitted. The first filing on an obligation runs through its lifecycle and freezes the lateness verdict; later filings insert without disturbing it. An amendment is a further filing, never a rewrite |
| `declare_incident_from_event` | Promote an assessed security event into an incident as one atomic act : creates the incident, carries over the event's title, timestamps, detection source, reporter, scopes and affected assets, declares it through its lifecycle, links the event and moves it to its confirmed step. Requires `incidents.event.validate` and `incidents.incident.create`, plus a mandatory rationale |
| `verify_evidence_integrity` | Re-measure an evidence artefact and append the result to its chain of custody. Returns one of three outcomes, never collapsed : `match`, `mismatch` (a permanent chain-of-custody break) and `not_verifiable` (a claim about the storage, not the artefact). The digest is measured, never asserted by the caller |
| `list_overdue_incident_notifications` | Every statutory deadline that has passed with no filing recorded : the "are we late" question in one call, with the regime, recipient, deadline, hours overdue and the incident and its manager. Obligations with no deadline, already filed, or in a terminal step are excluded |

## Accounts module

| Tool | Description |
| ---- | ----------- |
| `list_users` | List users with search and active status filter |
| `get_user` | Get detailed user information |
| `create_user` | Provision a user via the invitation flow (unusable password, returns a single-use `activation_url`) so it can be referenced as an owner / reviewer; assigns roles by name. Requires `system.users.create` |
| `get_me` | Get the currently authenticated user, including `can_override_import_dates` / `can_create_users` capability flags |
| `update_me` | Update the current user's profile (first_name, last_name, phone, language, timezone, theme_preference) |
| `get_dashboard_layout` | Get the current user's dashboard widget layout and the widget catalogue |
| `update_dashboard_layout` | Replace the current user's dashboard widget layout (ordered {id, size, visible}) |
| `list_saved_filters` | List the current user's saved list filters (own + shared), optionally by view_key |
| `create_saved_filter` | Save a named list filter (view_key, query, optional is_shared) |
| `delete_saved_filter` | Delete one of the current user's saved list filters |
| `list_notifications` | List the current user's in-app notifications with the unread count |
| `mark_notification_read` | Mark one of the current user's notifications as read |
| `mark_all_notifications_read` | Mark all of the current user's notifications as read |
| `list_groups` | List all groups |
| `get_group` | Get group details including permissions |
| `list_permissions` | List all available permissions with module filter |
| `list_access_logs` | List authentication events (login, logout, lockout) |

## Reports & Settings

| Tool | Description |
| ---- | ----------- |
| `list_reports` | List generated reports with optional type filter |
| `generate_soa_report` | Generate a Statement of Applicability (SoA) PDF for selected frameworks |
| `generate_audit_report` | Generate an audit report PDF for a completed assessment |
| `generate_risk_register` | Generate an Excel (.xlsx) export of the risk register with optional scope/assessment/status/priority filters |
| `generate_iso27005_report` | Generate an ISO 27005 risk assessment DOCX report for one assessment (context, criteria, threats, vulnerabilities, analyses, risks, plans, acceptances) |
| `generate_management_review_pptx` | Generate a management review PowerPoint presentation (ISO 27001 clause 9.3) |
| `generate_management_review_docx` | Generate a management review Word meeting minutes (ISO 27001 clause 9.3) |
| `list_management_reviews` | List persistent management reviews (ISO 27001:2022 clause 9.3) with status and scope filters |
| `get_management_review` | Get a management review with decision/change counts and snapshot state |
| `create_management_review` | Create a persistent management review |
| `transition_management_review` | Transition a management review through its life cycle (auto-snapshot on closure) |
| `export_management_review` | Export a management review as DOCX or PPTX (base64) |
| `list_management_review_decisions` | List decisions recorded during management reviews (clause 9.3.3 outputs) |
| `create_management_review_decision` | Record a decision from a management review |
| `promote_decision_to_action_plan` | Create a ComplianceActionPlan from a decision and link them |
| `list_isms_changes` | List ISMS changes decided during management reviews |
| `create_isms_change` | Record an ISMS change decided during a management review |
| `set_participant_signature` | Attach a base64 graphical signature (non-eIDAS) to a management review participant for DOCX embedding |
| `list_stakeholder_feedback` | List formal stakeholder feedback (clause 9.3.2.e) |
| `create_stakeholder_feedback` | Record formal feedback from an interested party |
| `delete_report` | Delete a generated report |
| `get_company_settings` | Get company settings (name, application name, AI assistant name, address, accent colour, whether the company logo replaces the Cairn logo) |
| `update_company_settings` | Update company settings (name, application name, AI assistant name, address, accent colour, use the company logo as the app brand) |

## Assistant

| Tool | Description |
| ---- | ----------- |
| `ask_assistant` | Ask the Ask Cairn natural-language assistant a read-only question about GRC data (e.g. "Which decisions were made at the last management review?"). Requires the optional assistant feature (`AI_ASSISTANT_ENABLED`, backed by a pluggable LLM provider); the answer cites real records and data access enforces the caller's permissions. See [docs/modules/assistant/](modules/assistant/README.md). |
